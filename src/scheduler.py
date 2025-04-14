import asyncio
import os
from datetime import datetime, time
import signal
import sys

from src.config import Config
from src.main import post_btc_update, setup_database

class Scheduler:
    def __init__(self, config=None):
        self.config = config or Config()
        self.running = False
        self.tasks = []
        
    async def scheduled_job(self):
        """Run the scheduled job"""
        current_time = datetime.utcnow()
        print(f"Running scheduled job at {current_time.isoformat()}")
        await post_btc_update(self.config)
    
    def parse_time(self, time_str):
        """Parse time string in format HH:MM"""
        hours, minutes = map(int, time_str.split(":"))
        return hours, minutes
    
    async def run(self):
        """Set up and run the scheduler"""
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Setup database with initial content if needed
        await setup_database()
        
        print("\nBTCBuzzBot Scheduler started")
        print(f"Timezone: {self.config.timezone}")
        print("Scheduled posting times:")
        for time_str in self.config.post_times:
            print(f"- {time_str}")
        print("\nPress Ctrl+C to stop\n")
        
        # Run the scheduler
        while self.running:
            current_time = datetime.utcnow()
            current_hour = current_time.hour
            current_minute = current_time.minute
            
            # Check if it's time to post
            for time_str in self.config.post_times:
                post_hour, post_minute = self.parse_time(time_str)
                
                if current_hour == post_hour and current_minute == post_minute:
                    # It's time to post
                    print(f"It's posting time! {time_str}")
                    task = asyncio.create_task(self.scheduled_job())
                    self.tasks.append(task)
            
            # Sleep until the next minute
            await asyncio.sleep(60 - current_time.second)
            
            # Cleanup completed tasks
            self.tasks = [task for task in self.tasks if not task.done()]
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._shutdown)
    
    def _shutdown(self):
        """Shutdown the scheduler gracefully"""
        print("\nShutting down scheduler...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Exit
        sys.exit(0)

async def main():
    """Main function"""
    scheduler = Scheduler()
    await scheduler.run()

if __name__ == "__main__":
    # Run the scheduler
    asyncio.run(main()) 