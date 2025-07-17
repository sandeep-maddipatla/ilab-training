# SPDX-License-Identifier: Apache-2.0

# Standard
import os

# Third Party
from datasets import load_dataset
from torch.utils.data import DataLoader, Dataset
import numpy as np
import torch

# First Party
from instructlab.training.multipack_sampler import MultipackDistributedBatchSampler
from instructlab.training.utils import log_rank_0, make_collate_fn, pad_batch

from instructlab.training.hpu_utils import bucket, batch_bucket

class TokenDataset(Dataset):
    def __init__(self, data_path):
        self.data = load_dataset("json", data_files=data_path, split="train")
        if "len" not in self.data.column_names:
            self.lengths = np.array(
                self.data.map(
                    lambda x: {"len": len(x["input_ids"])},
                    num_proc=8,
                )["len"]
            )
        else:
            self.lengths = np.array(self.data["len"])

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[int(idx)]
        input_ids = torch.tensor(item["input_ids"], dtype=torch.long)
        labels = torch.tensor(item["labels"], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)

        return {
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": attention_mask,
        }

    def get_lengths(self):
        return self.lengths


class MockDataset(Dataset):
    def __init__(self, max_seq_len=4600):
        self.input_ids = np.random.randint(
            0, 10000, size=(92000, max_seq_len), dtype=np.int16
        )
        self.labels = np.random.randint(
            0, 10000, size=(92000, max_seq_len), dtype=np.int16
        )

    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        input_ids = torch.tensor(self.input_ids[idx], dtype=torch.long)
        labels = torch.tensor(self.labels[idx], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)

        return {
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": attention_mask,
        }

    def get_lengths(self):
        return np.array([len(self.input_ids[0])] * len(self.input_ids))


def setup_dataset(
    data_path: str,
    mock: bool = False,
    mock_len: int = 2600,
) -> Dataset:
    if mock:
        log_rank_0("Using a mock dataset.")
        dataset = MockDataset(max_seq_len=mock_len)
    else:
        dataset = TokenDataset(data_path)
    return dataset

def print_batches(dataloader, rank=0, epoch=0,max_batches=50):
    """
    Print the names and shapes of all tensor inputs across the first few batches.
    """
    print("Printing input tensor shapes for batches:")
    for batch_idx, batch in enumerate(dataloader):
        if batch_idx >= max_batches:
            break
        print(f"[BATCH_PRINT] rank:{rank}, epoch: {epoch},  Batch {batch_idx}:")
        if isinstance(batch, dict):
            for name, tensor in batch.items():
                if hasattr(tensor, "shape"):
                    print(f"[BATCH_PRINT] rank:{rank}, epoch: {epoch},   {name}: {tensor.shape}")
                else:
                    print(f"[BATCH_PRINT] rank:{rank}, epoch: {epoch},   {name}: {type(tensor)}")
        elif isinstance(batch, (list, tuple)):
            for i, item in enumerate(batch):
                if hasattr(item, "shape"):
                    print(f"[BATCH_PRINT] rank:{rank}, epoch: {epoch},   input_{i}: {item.shape}")
                else:
                    print(f" [BATCH_PRINT] rank:{rank}, epoch: {epoch},  input_{i}: {type(item)}")
        else:
            print(f"[BATCH_PRINT] rank:{rank}, epoch: {epoch},   batch: {type(batch)}")
        print(f"[BATCH_PRINT] rank:{rank}, epoch: {epoch}" + "-" * 40)

def process_batches(dataloader, rank=0, epoch=0):
    """
    Process the batches to determine the bucketed sizes.
    """
    print_batches(dataloader, rank=rank, epoch=epoch)
    
    lengths = []

    for batch_idx, batch in enumerate(dataloader):
        if isinstance(batch, dict):
            lengths.append(batch["input_ids"].shape[0])
        elif isinstance(batch, (list, tuple)):
            lengths.append([item.shape[0] for item in batch if hasattr(item, "shape")])
    
    lengths = np.array(lengths)
    bucketed_sizes = batch_bucket(lengths)
    
    print(f"[BATCH_PRINT] rank:{rank} epoch:{epoch}, lengths={lengths}, Bucketed sizes: {bucketed_sizes}")
    
    return bucketed_sizes

def setup_dataloader(
    dataset: Dataset,
    pad_token_id: int,
    num_workers: int = 8,
    flash_enabled=True,
    max_batch_len=60000,
    packing_max_batch_len=60000,
    samples_per_gpu=None,
    sampler="multipack",
    seed=47,
    device=None,
) -> DataLoader:
    collate_fn = make_collate_fn(
        pad_token_id, flash_enabled=flash_enabled, max_batch_len=max_batch_len,
        device=device,
    )
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])

    lengths = dataset.get_lengths()
    if sampler == "multipack":
        if device == "hpu":
            bucket_v = np.vectorize(bucket)
            lengths = bucket_v(lengths)

        sampler = MultipackDistributedBatchSampler(
            batch_max_length=packing_max_batch_len,
            lengths=lengths,
            num_replicas=world_size,
            rank=rank,
            seed=seed,
            padding=not flash_enabled,
        )
        sampler = {"batch_sampler": sampler}
    elif sampler == "distributed":
        # Third Party
        from torch.utils.data import DistributedSampler

        sampler = (
            DistributedSampler(dataset) if torch.distributed.is_initialized() else None
        )
        sampler = {
            "sampler": sampler,
            "batch_size": samples_per_gpu,
        }
    else:
        raise NotImplementedError

    dataloader = DataLoader(
        dataset,
        **sampler,
        num_workers=num_workers,
        collate_fn=collate_fn,
    )

    return dataloader
