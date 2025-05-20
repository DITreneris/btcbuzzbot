"""
Command-line interface for controlling the scheduler.
"""

import sys
import os
import time
import logging
import asyncio
import signal

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Engine control functions
try:
    from src.scheduler_engine import start as engine_start, stop as engine_stop, scheduler_instance
    ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"Error importing scheduler engine: {e}")
    ENGINE_AVAILABLE = False

# Manual task trigger functions
try:
    from src.scheduler_tasks import trigger_post_tweet, trigger_fetch_news, trigger_analyze_news
    TASKS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing scheduler tasks: {e}")
    TASKS_AVAILABLE = False

logger = logging.getLogger('btcbuzzbot.scheduler.cli')

# --- New Async Runner for Start Command ---
async def run_scheduler():
    """Starts the engine and keeps the event loop running until interrupted."""
    if not ENGINE_AVAILABLE:
        logger.error("Cannot start: Scheduler engine not available.")
        return False # Indicate failure

    if await engine_start(): # Call async version
        print("Scheduler engine initialized. Running... Press Ctrl+C to exit.")
        
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        
        # Add signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                 # Windows doesn't support add_signal_handler reliably
                 # The KeyboardInterrupt exception handler below will be the primary mechanism
                 pass 
                 
        try:
            await stop_event.wait() # Keep running until event is set
        finally:
            # Clean up signal handlers if they were set
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.remove_signal_handler(sig)
                except NotImplementedError:
                     pass
                     
            print("\nInterrupt received, shutting down scheduler...")
            await engine_stop() 
            print("Scheduler stopped.")
        return True # Indicate success
    else:
        print("Failed to initialize scheduler engine.")
        return False # Indicate failure

def print_usage():
    print("Usage: python -m src.scheduler_cli [start|stop|status|tweet|fetch_news|analyze_news]")
    print("  start         - Start the scheduler in the background")
    print("  stop          - Attempt to stop the scheduler (if started in same process)")
    print("  status        - Show scheduler status and active jobs")
    print("  tweet         - Manually trigger a tweet post")
    print("  fetch_news    - Manually trigger a news fetch cycle")
    print("  analyze_news  - Manually trigger a news analysis cycle")
    print("Note: 'stop' command is unreliable; use process management (Ctrl+C, systemd, etc.)")

def main():
    # Basic logging for CLI itself
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "start":
        # Replace old start logic with asyncio runner
        try:
            if not asyncio.run(run_scheduler()):
                sys.exit(1) # Exit if run_scheduler indicated failure
        except KeyboardInterrupt:
            # Handle Ctrl+C if signal handler didn't catch it (e.g., during setup)
            # The run_scheduler's finally block should handle shutdown if it got far enough
            print("\nKeyboard interrupt detected during startup/shutdown.")
            # Attempt stop again just in case? Might be redundant.
            # if ENGINE_AVAILABLE: engine_stop()
            sys.exit(0)
        # Exit normally after graceful shutdown
        sys.exit(0)

    elif command == "status":
        if not ENGINE_AVAILABLE:
             logger.error("Cannot get status: Scheduler engine not available.")
             sys.exit(1)
             
        # Check status via the engine instance
        if scheduler_instance and scheduler_instance.running:
            print("Scheduler is running (in this process).")
            jobs = scheduler_instance.get_jobs()
            print(f"Active jobs ({len(jobs)}):")
            for job in jobs:
                next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else 'None'
                print(f"  - ID: {job.id:<25} Name: {job.name:<30} Trigger: {str(job.trigger):<35} Next Run: {next_run}")
        else:
             # TODO: Enhance status check? Query DB? 
             print("Scheduler not running (in this process).")

    elif command == "stop":
        if not ENGINE_AVAILABLE:
             logger.error("Cannot stop: Scheduler engine not available.")
             sys.exit(1)
        print("Attempting to stop scheduler (only works if started in same process)...")
        try:
            stopped = asyncio.run(engine_stop()) # Run the async stop function
            if stopped:
                 print("Stop command sent to scheduler instance.")
            else:
                 print("Stop command failed or scheduler wasn't running in this process.")
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                 logger.error("Cannot run manual stop command while scheduler is running in this terminal.")
                 logger.error("Use Ctrl+C in the running terminal instead.")
            else:
                 logger.error(f"Error running stop command: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error running stop command: {e}")
            sys.exit(1)

    elif command == "tweet":
        if not TASKS_AVAILABLE:
             logger.error("Cannot trigger tweet: Tasks module not available.")
             sys.exit(1)
        # Wrap potentially async task trigger
        try:
             result = asyncio.run(trigger_post_tweet()) # Assume trigger_post_tweet might be async now
             if result:
                 print("Tweet posted successfully (triggered manually).")
             else:
                 print("Failed to post tweet (triggered manually).")
        except Exception as e:
            logger.error(f"Error triggering manual tweet: {e}", exc_info=True)
            sys.exit(1)

    elif command == "fetch_news":
        if not TASKS_AVAILABLE:
             logger.error("Cannot trigger fetch: Tasks module not available.")
             sys.exit(1)
        # Wrap potentially async task trigger
        try:
            print("Triggering manual news fetch...")
            asyncio.run(trigger_fetch_news()) # Assume trigger_fetch_news is async
            print("Manual news fetch cycle triggered (runs in background).")
        except Exception as e:
            logger.error(f"Error triggering manual fetch: {e}", exc_info=True)
            sys.exit(1)

    elif command == "analyze_news":
        if not TASKS_AVAILABLE:
             logger.error("Cannot trigger analysis: Tasks module not available.")
             sys.exit(1)
        # Wrap potentially async task trigger
        try:
            print("Triggering manual news analysis...")
            asyncio.run(trigger_analyze_news()) # Assume trigger_analyze_news is async
            print("Manual news analysis cycle triggered (runs in background).")
        except Exception as e:
            logger.error(f"Error triggering manual analysis: {e}", exc_info=True)
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)

if __name__ == "__main__":
    main() 