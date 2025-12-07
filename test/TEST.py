from src.market_history import market_history_obj
from src.strategy.record_HL.manager import HLRecordManager
from src.settings import settings_obj, strategies_obj
from src.constants import FILE_PATH_HIST_STRATEGY, FILE_PATH_FEAR_GREAD
from src.strategy.fear_gread.fear_gread import FearAndGread
from src.strategy import trade_manager_obj, Trade
import time
from src.binance import kline_stream, disconnect_stream, StreamKline,stream_manager_obj
import threading
import asyncio

#record = HighLowManager(FILE_PATH_HIST_STRATEGY, strategies_class.id_pair_list)
#fear_gread = FearAndGread(FILE_PATH_FEAR_GREAD)

pair = "BTCUSDC"
kline = StreamKline(1764187215000, 90900, 88000,99000,81000,5000, "1d")

#stream_data_class.set(pair, kline)

if False:
      print(f"history.data.keys() {market_history_obj.run(500000)}")
#print(f"history.data[BTCUSDC].intervals.keys() {history_class.data["BTCUSDC"].intervals.keys()}")

print(f"strategies_class.generate_pairs_intervals() {strategies_obj.generate_pairs_intervals()}")

print(f"stream_data_class.data() {stream_manager_obj._data}")

#print(f"record.get {record.get("5_BTCUSDC")}")
#print(f"record.data {record.data}")

#print(f"fear_gread {fear_gread.data}")
#Strategy = strategies_class.get_by_id(1111)
#Strategy["Symbol1"] = "ETH"
#Strategy["name"] = "Advance DCA Etherium"# "Testing manager update"
#strategies_class.update(4,Strategy) ""
#trade : Trade = trade_manager_class.get_open(5, 600000)
#print(f"trade_manager_class data {trade}")
#print(f"trade_manager_class data {trade_manager_class.data[5].trades[-1]}")
#trade_manager_class.new_trade(trade,4)
#trade.idx="Test hopla"
#print(f"trade_manager_class data {trade}")
#print(trade_manager_class.set_close(5, trade))
#print(f"trade_manager_class data {trade_manager_class.data.keys()}")

#



#threads event
stop = False
#---------------------Streaming task Thread -----LOOP2------------------
def RUN_StreamLoop():
    print(f"RUN_StreamLoop() New thread Start") 
    backoff_attempt = 0
    backoff_base = 1.5
    reconnectPause = 30
    while not stop:
        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)
        task = None 
        try:
            task = loop2.create_task(kline_stream(
                loop_runtime=settings_obj.get("klineStreamLoopRuntime"),
                max_no_data=5,
                init_interval_ind=1
            ))
            loop2.run_until_complete(task)
        except Exception as e:
            print(f"RUN_StreamLoop(): top-level exception: {e}")

        # Cancel any remaining tasks before closing the loop
        pending = asyncio.all_tasks(loop=loop2)
        for t in pending:
            t.cancel()
        loop2.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop2.close()

        if not stop:
            # Backoff before attempting a clean fresh reconnect
            backoff_attempt += 1
            sleep_time = min(reconnectPause * (backoff_base ** (backoff_attempt - 1)), 120)
            print(f"RUN_StreamLoop() stopped unexpectedly - restarting after {sleep_time} s")
            time.sleep(sleep_time)

    print(f"RUN_StreamLoop() Thread Stopped") 



if __name__ == "__main__":        
      Stream_thread = threading.Thread(target=RUN_StreamLoop)
      Stream_thread.daemon = False
      Stream_thread.start()

      i = 8
      # Create and start the Stream loop thread
      while i > 0:
            print(f"{i} s")
            i -=1
            time.sleep(1)

 # The main thread can continue to run or wait
      try:
            i = 120
            while i > 0:      
                  i -=1     
            # Main thread activity    
                  print(f"stream_data_class.get_active_list() {stream_manager_obj.get_active_list()}")
                  print(f"stream_data_class.oldest() {stream_manager_obj.oldest()}")
                  print(f"stream_data_class.all_streams_available() {stream_manager_obj.all_streams_available()}")
                  print(f"{i} s")
                  time.sleep(1) #Will sleap for strategy update time
      except KeyboardInterrupt:
            print("Program terminated by user...")
      stop = True
      time.sleep(5)
      disconnect_stream()
      print(f"stream_data_class.data() {stream_manager_obj._data}")





