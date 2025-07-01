import re
import sys
import statistics
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

### Usage documentation
#
# pip install perfetto pandas numpy
#

def get_bwd_pass_start_ts(autograd_slices):
    # Return 0 is autograd_slices is None
    if not autograd_slices:
        print('Warning: autograd_slices is None. Default 0 returned')
        return 0

    for s in autograd_slices:
        # Return time stamp of first slice in the autograd slices
        # There is probably a better way to do this
        return s.ts

def process_tpc_slices_fwd(tpc_slices, start_ts=0, end_ts=float('inf')):
    layer_ts_list = []

    ## Parse slices to identify layer start and layer end timestamps
    layer_start_ts = None
    layer_end_ts = None
    for s in tpc_slices:
        if s.ts < start_ts:
            continue
        
        if s.name and 'rms_norm_fwd_bf16' in s.name:
            # there are two rms_norms per layer. Every alternate one indicates start of an attention layer
            if not layer_start_ts:
                layer_start_ts = s.ts
        elif s.name and 'memcpy_u8' in s.name:
            # an attention layer (except the last one) ends with a memcpy_u8 block
            if layer_start_ts:
                # One of the early layers have an extra memcpy_u8. Ignore this as it is not related to an attn layer
                layer_end_ts = s.ts + s.dur
                layer_ts_list.append({ 'start': layer_start_ts, 'end': layer_end_ts, 'duration': layer_end_ts - layer_start_ts , 'bubble': 0 if not layer_ts_list else layer_start_ts - layer_ts_list[-1]['end']})
                layer_start_ts = None
                layer_end_ts = None
        elif s.name and 'logsoftmax_fwd_f32' in s.name:
            # last attn layer has a pair of logsoftmax instead of memcpy_u8 
            # (there are a few more ops after the logsoftmax, but they are small and not uniquely identifiable) for a simple parser like this
            # we will approximate that it will end at the second logsoftmax
            if layer_end_ts:
                layer_end_ts = s.ts + s.dur
                layer_ts_list.append({ 'start': layer_start_ts, 'end': layer_end_ts, 'duration': layer_end_ts - layer_start_ts, 'bubble': 0 if not layer_ts_list else layer_start_ts - layer_ts_list[-1]['end']})
                layer_start_ts = None
                layer_end_ts = None
            else:
                layer_end_ts = s.ts + s.dur
            
        if s.ts > end_ts:
            # We have started hitting blocks from the bwd pass
            # Can end this here.
            break
    
    print(f'{len(layer_ts_list)=}')
    layer_durations = [x['duration']/1000000 for x in layer_ts_list]
    print(f'Duration Time in milliseconds: {layer_durations}')
    bubble_times = [x['bubble']/1000000 for x in layer_ts_list]
    print(f'Bubble Time in milliseconds: {bubble_times}')


def capture_stats(tpc_slices, mme_slices, host_fwd_pass_slices=None, host_bwd_pass_slices=None):

    bwd_pass_start_ts = get_bwd_pass_start_ts(host_bwd_pass_slices)
    process_tpc_slices_fwd(tpc_slices, end_ts=bwd_pass_start_ts)


    return 0

def analyse_trace(trace_path):
    tp = TraceProcessor(trace=trace_path)

    processes = tp.query("""
        SELECT upid, pid, name, cmdline, start_ts FROM process
    """)

    mme_slices = None
    tpc_slices = None
    fwd_slices = None
    autograd_slices = None

    print(f'{processes=}')
    for p in processes:
        print(f"Process ID: {p.upid}, PID:{p.pid} Name: {p.name}, Cmdline: {p.cmdline}, Start time: {p.start_ts}")
        threads = tp.query(f"""
            SELECT utid, tid, name, upid, start_ts FROM thread WHERE upid = {p.upid}
        """)
        for t in threads:
            tracks = tp.query(f"""
                SELECT track.id AS track_id,  track.name AS track_name, track.type AS track_type,  thread.utid FROM track
                JOIN thread_track ON track.id = thread_track.id
                JOIN thread ON thread_track.utid = thread.utid
                WHERE thread.utid = {t.utid}
            """)

            track_count = len(tracks) if tracks else 0

            track_id_list = []
            slice_count = 0
            for tr in tracks:
                track_id_list.append(tr.track_id)
                slices = tp.query(f"""
                    SELECT ts, dur, name, category FROM slice WHERE track_id = {tr.track_id} ORDER BY ts
                """)
                slice_count += len(slices) if slices else 0
                if t.name and '[HD0] TPC 0' in t.name:
                    tpc_slices = slices
                elif t.name and '[HD0] MME' in t.name:
                    mme_slices = slices
                elif t.name and 'pt_autograd' in t.name:
                    autograd_slices = slices
                elif t.name and 'python3' in t.name:
                    fwd_slices = slices
            
            if slice_count !=0 and track_count != 0:
                print(f"\tThread ID: {t.utid}, PID:{t.tid} Name: {t.name}, Start time: {t.start_ts}, {track_count=}, {track_id_list=}, {slice_count=}")


    capture_stats(tpc_slices, mme_slices, fwd_slices, autograd_slices)
    
    '''
    x = tp.query("select * from slice where id=344204")
    import pdb; pdb.set_trace()        

    tracks = tp.query('select id, name, type, source_arg_set_id from track')
    for t in tracks:
        print(f'{t.id=}, {t.name=}, {t.type=}, {t.source_arg_set_id=}')

    res_it = tp.query('select * from slice limit 10')
    for row in res_it:
        print(row.name)
        
    # Convert QueryResultIterator into a pandas dataframe + iterate. This yields
    # the same results as the function above.
    try:
        res_df = tp.query('select * from slice limit 10').as_pandas_dataframe()
        for index, row in res_df.iterrows():
            print(row['name'])
    except Exception as e:
        print(f'Hit Exception: {e}')
    '''

def main():
    if len(sys.argv) != 2:
        print("Usage: python process_profile.py <trace_file>")
        sys.exit(1)
    
    trace_path = sys.argv[1]
    analyse_trace(trace_path)
    

if __name__ == "__main__":  
    main()