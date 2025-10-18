import schedule
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from backend.config import config
from backend.ingestion import ingestion_pipeline
from backend.database import db_manager

class DailyScheduler:
    """Daily job scheduler for Morning Brief generation"""
    
    def __init__(self):
        self.running = False
        self.scheduler_thread = None
        self.last_run = None
        self.last_success = None
        self.last_error = None
        
        # Configure logging
        self._setup_logging()
        
        # Schedule the daily job
        self._schedule_jobs()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, "INFO"),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/scheduler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('scheduler')
    
    def _schedule_jobs(self):
        """Schedule daily jobs"""
        # Schedule daily ingestion at 6 AM UTC
        schedule.every().day.at("06:00").do(self._run_ingestion_job)
        
        # Schedule cleanup job weekly (Sundays at 2 AM)
        schedule.every().sunday.at("02:00").do(self._run_cleanup_job)
        
        # Schedule health check every hour
        schedule.every().hour.do(self._run_health_check)
        
        self.logger.info("Scheduled jobs configured")
    
    def _run_ingestion_job(self):
        """Run the daily ingestion job"""
        try:
            self.logger.info("Starting daily ingestion job")
            self.last_run = datetime.utcnow()
            
            # Run ingestion pipeline
            result = ingestion_pipeline.ingest_pipeline()
            
            if result['success']:
                self.last_success = datetime.utcnow()
                self.last_error = None
                self.logger.info(f"Ingestion job completed successfully: {result['message']}")
            else:
                self.last_error = result['message']
                self.logger.error(f"Ingestion job failed: {result['message']}")
            
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Ingestion job error: {e}")
    
    def _run_cleanup_job(self):
        """Run weekly cleanup job"""
        try:
            self.logger.info("Starting weekly cleanup job")
            
            # Clean up old articles (older than 90 days)
            deleted_count = db_manager.cleanup_old_articles(days=90)
            
            self.logger.info(f"Cleanup job completed: removed {deleted_count} old articles")
            
        except Exception as e:
            self.logger.error(f"Cleanup job error: {e}")
    
    def _run_health_check(self):
        """Run hourly health check"""
        try:
            # Check database connection
            article_count = db_manager.get_article_count()
            
            # Check if we have recent articles
            recent_articles = db_manager.get_recent_articles(limit=1, days=1)
            has_recent_articles = len(recent_articles) > 0
            
            # Log health status
            self.logger.info(f"Health check: {article_count} total articles, recent articles: {has_recent_articles}")
            
            # Alert if no recent articles for more than 2 days
            if not has_recent_articles and self.last_success:
                days_since_success = (datetime.utcnow() - self.last_success).days
                if days_since_success > 2:
                    self.logger.warning(f"No recent articles for {days_since_success} days")
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
    
    def start(self):
        """Start the scheduler in a background thread"""
        if self.running:
            self.logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            self.logger.warning("Scheduler is not running")
            return
        
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        self.logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        return {
            'running': self.running,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_error': self.last_error,
            'next_run': self._get_next_run_time(),
            'scheduled_jobs': len(schedule.jobs)
        }
    
    def _get_next_run_time(self) -> Optional[str]:
        """Get next scheduled run time"""
        try:
            next_run = schedule.next_run()
            return next_run.isoformat() if next_run else None
        except:
            return None
    
    def run_ingestion_now(self) -> Dict[str, Any]:
        """Manually trigger ingestion job"""
        try:
            self.logger.info("Manual ingestion triggered")
            self._run_ingestion_job()
            
            return {
                'success': True,
                'message': 'Manual ingestion completed',
                'last_run': self.last_run.isoformat() if self.last_run else None,
                'last_success': self.last_success.isoformat() if self.last_success else None,
                'last_error': self.last_error
            }
        except Exception as e:
            self.logger.error(f"Manual ingestion error: {e}")
            return {
                'success': False,
                'message': f'Manual ingestion failed: {str(e)}',
                'last_run': self.last_run.isoformat() if self.last_run else None,
                'last_error': str(e)
            }
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        try:
            stats = ingestion_pipeline.get_ingestion_stats()
            stats.update({
                'scheduler_status': self.get_status(),
                'last_ingestion': self.last_success.isoformat() if self.last_success else None
            })
            return stats
        except Exception as e:
            self.logger.error(f"Error getting ingestion stats: {e}")
            return {
                'error': str(e),
                'scheduler_status': self.get_status()
            }

# Global scheduler instance
daily_scheduler = DailyScheduler()
