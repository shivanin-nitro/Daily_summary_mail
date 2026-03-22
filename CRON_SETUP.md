# Daily Summary Mail Pipeline - Cron Job Setup Guide

## Overview

This document explains how to set up and manage the Daily Summary Mail pipeline to run automatically at 11:00 AM every day using a cron job.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding the Setup](#understanding-the-setup)
3. [Installation Steps](#installation-steps)
4. [Verification](#verification)
5. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
6. [Management](#management)

---

## Quick Start

To install the cron job immediately, run:

```bash
bash setup_cron.sh
```

That's it! The pipeline will now run every day at **11:00 AM**.

---

## Understanding the Setup

### Components

The cron job setup consists of three key files:

#### 1. **`main.py`** - Main Pipeline Script
- Contains the `run_pipeline()` function that:
  - Fetches availability and SOV data from ClickHouse
  - Processes data for each brand
  - Generates AI insights using Groq API
  - Sends formatted email summaries with attachments
  - Handles all logging and error management

#### 2. **`run_pipeline.sh`** - Wrapper Script
- Bash script that acts as the cron job executable
- Activates the Python virtual environment (`.venv`)
- Runs the main pipeline script
- Ensures proper environment variables and dependencies are loaded
- Critical for cron jobs (they run with minimal environment)

#### 3. **`setup_cron.sh`** - Installation Script
- Automates the cron job installation
- Makes `run_pipeline.sh` executable
- Prevents duplicate cron entries
- Sets up logging directory
- Creates an easy uninstall path

---

## Installation Steps

### Step 1: Prerequisites

Ensure you have:
- Python 3.11+ installed
- Virtual environment activated at least once: `source .venv/bin/activate`
- `.env` file with all required credentials configured
- `logs/` directory exists (will be created if missing)

### Step 2: Make Scripts Executable

```bash
chmod +x run_pipeline.sh
chmod +x setup_cron.sh
```

### Step 3: Run the Setup Script

```bash
bash setup_cron.sh
```

**Output:**
```
📋 Setting up cron job for Daily Summary Mail Pipeline...
📁 Project directory: /Users/manpreetsingh/Desktop/PRIVATE GIT/Daily_summary_mail
🔧 Script path: /Users/manpreetsingh/Desktop/PRIVATE GIT/Daily_summary_mail/run_pipeline.sh
✅ Cron job installed successfully!
⏰ The pipeline will run every day at 11:00 AM
📊 Logs will be written to: /Users/manpreetsingh/Desktop/PRIVATE GIT/Daily_summary_mail/logs/cron.log
```

### Step 4: Verify Installation

Check that the cron job was installed:

```bash
crontab -l
```

You should see an entry like:
```
0 11 * * * /Users/manpreetsingh/Desktop/PRIVATE\ GIT/Daily_summary_mail/run_pipeline.sh >> /Users/manpreetsingh/Desktop/PRIVATE\ GIT/Daily_summary_mail/logs/cron.log 2>&1
```

---

## Cron Job Syntax Explained

The installed cron job follows this format:

```
0 11 * * * /path/to/run_pipeline.sh >> /path/to/logs/cron.log 2>&1
│ │  │ │ │
│ │  │ │ └─ Day of Week (0-6, 0 is Sunday) - * means every day
│ │  │ └──── Month (1-12) - * means every month
│ │  └────── Day of Month (1-31) - * means every day
│ └────────── Hour (0-23) - 11 means 11:00 AM
└──────────── Minute (0-59) - 0 means on the hour
```

**Current Configuration:**
- ⏰ **Time**: 11:00 AM (0 11)
- 📅 **Frequency**: Every day, every month
- 📊 **Logs**: Redirected to `logs/cron.log`

---

## Verification

### Check if Cron Job is Running

After 11 AM on any day, check the cron logs:

```bash
tail -f logs/cron.log
```

You should see logs indicating:
- Pipeline started
- Connections established
- Data fetched and processed
- Emails sent
- Pipeline completed

### Manual Test Run

To test the pipeline manually (outside of cron):

```bash
bash run_pipeline.sh
```

Or directly:

```bash
source .venv/bin/activate
python main.py
```

### Check System Cron Logs

On macOS, view system cron logs:

```bash
log stream --predicate 'process == "cron"' --level debug
```

---

## Monitoring & Troubleshooting

### View Cron Logs

```bash
# View last 50 lines
tail -50 logs/cron.log

# Follow logs in real-time
tail -f logs/cron.log

# Search for errors
grep ERROR logs/cron.log

# Search for specific brand
grep "PINQ POLKA" logs/cron.log
```

### Common Issues & Solutions

#### Issue: Cron job not running

**Possible Causes:**
1. Virtual environment path is incorrect
2. Script path changed or moved
3. `.env` file is missing or incomplete

**Solution:**
- Verify script location hasn't changed
- Re-run `setup_cron.sh` to update paths
- Check `.env` file has all required variables

#### Issue: "Command not found" in logs

**Possible Causes:**
1. `run_pipeline.sh` is not executable
2. Virtual environment doesn't exist

**Solution:**
```bash
chmod +x run_pipeline.sh
source .venv/bin/activate  # Verify venv exists
```

#### Issue: Python module not found errors

**Possible Causes:**
1. Dependencies not installed in virtual environment
2. Wrong Python environment being used

**Solution:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

#### Issue: Email not being sent

**Possible Causes:**
1. SENDER_EMAIL or SENDER_PASSWORD missing in `.env`
2. Gmail app-specific password needed
3. ClickHouse connection failing

**Solution:**
- Verify all credentials in `.env`
- Check `logs/cron.log` for connection errors
- Test manually: `bash run_pipeline.sh`

### Debug Mode

To see more detailed logs, modify `run_pipeline.sh`:

```bash
# Add verbose flag
python main.py --verbose
```

Or check the pipeline logging configuration in `src/logging_config.py`.

---

## Management

### View All Cron Jobs

```bash
crontab -l
```

### Edit Cron Jobs

```bash
crontab -e
```

This opens the crontab file in your default editor. You can:
- Modify the time (change `0 11` to a different hour/minute)
- Add comments (lines starting with `#`)
- Remove the job (delete the line)

### Change Execution Time

Edit crontab and modify the hour:

```bash
# Current: 11:00 AM
0 11 * * *

# Examples:
0 9 * * *    # 9:00 AM
30 14 * * *  # 2:30 PM
0 0 * * *    # Midnight (12:00 AM)
```

### Remove the Cron Job

#### Option 1: Edit crontab directly

```bash
crontab -e
```

Find and delete the line with `run_pipeline.sh`, then save.

#### Option 2: Clear all cron jobs

```bash
crontab -r
```

⚠️ This removes ALL cron jobs, not just this one.

### Create a New Cron Job (Manual)

If you want to add another time slot:

```bash
crontab -e
```

Add a new line:
```bash
0 15 * * * /Users/manpreetsingh/Desktop/PRIVATE\ GIT/Daily_summary_mail/run_pipeline.sh >> /Users/manpreetsingh/Desktop/PRIVATE\ GIT/Daily_summary_mail/logs/cron.log 2>&1
```

This would run the pipeline at both 11 AM and 3 PM.

---

## Logs & Output

### Log Location

```
/Users/manpreetsingh/Desktop/PRIVATE GIT/Daily_summary_mail/logs/cron.log
```

### Log Format

```
[2026-03-22 11:00:05] ============================================================
[2026-03-22 11:00:05] 🚀  Starting Daily Summary Mail Pipeline
[2026-03-22 11:00:05] ============================================================
[2026-03-22 11:00:06] ✅  ClickHouse connection established
[2026-03-22 11:00:15] 🚀  Processing: PINQ POLKA
[2026-03-22 11:00:20] ✅  Email sent → brand_manager@example.com
[2026-03-22 11:00:45] ✅  Pipeline complete.
```

### Archiving Logs

To keep logs manageable, periodically clean old logs:

```bash
# Keep only last 100 lines
tail -100 logs/cron.log > logs/cron.log.tmp && mv logs/cron.log.tmp logs/cron.log

# Or use log rotation (add to setup)
```

---

## Advanced Configuration

### Running Multiple Times Per Day

Edit crontab (`crontab -e`) and add multiple lines:

```bash
0 8 * * * /path/to/run_pipeline.sh >> /path/to/logs/cron.log 2>&1    # 8 AM
0 11 * * * /path/to/run_pipeline.sh >> /path/to/logs/cron.log 2>&1   # 11 AM
0 14 * * * /path/to/run_pipeline.sh >> /path/to/logs/cron.log 2>&1   # 2 PM
```

### Running Only on Weekdays

Modify the day-of-week field (last `*`):

```bash
0 11 * * 1-5 /path/to/run_pipeline.sh >> /path/to/logs/cron.log 2>&1
```

`1-5` = Monday through Friday

### Running on Specific Days

```bash
0 11 1 * * /path/to/run_pipeline.sh >> /path/to/logs/cron.log 2>&1
```

This runs on the 1st of every month at 11 AM.

---

## Environment Variables

The pipeline requires these variables in `.env`:

```
GROQ_API_KEY=your_groq_api_key
CLICKHOUSE_HOST=your_clickhouse_host
CLICKHOUSE_USER=your_clickhouse_user
CLICKHOUSE_PORT=9000
CLICKHOUSE_PASS=your_clickhouse_password
CLICKHOUSE_DB=your_database_name
CLICKHOUSE_INTERNAL_HOST=internal_host
SENDER_EMAIL=your_gmail@gmail.com
SENDER_PASSWORD=your_app_specific_password
DASHBOARD_URL=your_dashboard_url
```

⚠️ **Important**: The `.env` file is loaded by the Python script, so cron can access these variables.

---

## Troubleshooting Checklist

- [ ] Run `bash setup_cron.sh` successfully
- [ ] Verify with `crontab -l`
- [ ] Test manually: `bash run_pipeline.sh`
- [ ] Check logs: `tail logs/cron.log`
- [ ] Verify `.env` file exists and is complete
- [ ] Confirm virtual environment has all dependencies: `pip list`
- [ ] Check ClickHouse connection manually
- [ ] Verify email credentials work manually
- [ ] Review cron system logs

---

## Support & Questions

For issues or questions:
1. Check the logs: `tail logs/cron.log`
2. Test manually: `bash run_pipeline.sh`
3. Review the troubleshooting section above
4. Check individual module logs in `logs/` directory

---

**Last Updated**: March 22, 2026  
**Pipeline Version**: 1.0  
**Python Version**: 3.11+  
**Cron Status**: Automated Daily at 11:00 AM
