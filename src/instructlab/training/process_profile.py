import re
import sys
import statistics
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

### Usage documentation
#
# pip install perfetto pandas numpy
#

def capture_stats(mme_slices, tpc_slices, host_fwd_pass_slices):
    count = 0
    for s in mme_slices:
        print(f'{s.__dict__=}')
        count += 1
        if count == 10:
            break
    return 0

def analyse_trace(trace_path):
    tp = TraceProcessor(trace=trace_path)

    processes = tp.query("""
        SELECT upid, pid, name, cmdline, start_ts FROM process
    """)

    mme_slices = None
    tpc_slices = None

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
                if '[HD0] TPC 0' in t.name:
                    tpc_slices = slices
                elif '[HD0] MME' in t.name:
                    mme_slices = slices
            
            if slice_count !=0 and track_count != 0:
                print(f"\tThread ID: {t.utid}, PID:{t.tid} Name: {t.name}, Start time: {t.start_ts}, {track_count=}, {track_id_list=}, {slice_count=}")


    capture_stats(mme_slices, tpc_slices)
    
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