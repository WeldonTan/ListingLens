import asyncio
import aiohttp
import time
import json
import random
import sys # Import sys for exit codes

API_URL = "http://localhost:8000/api/v1"

# A list of dummy URLs or real ones if available. 
# Since we are testing queueing, the validity of the URL matters less than the fact that it triggers the worker.
# However, the scraper might fail fast on invalid URLs.
# Real links provided by user
URLS = [
    "https://www.mudah.my/starhill-condominium-healthy-living-in-a-rare-corner-unit-110287314.htm",
    "https://www.mudah.my/millennium-court-corner-unit-kepayan-kkia-low-density-for-sale-113074225.htm",
    "https://www.mudah.my/hot-area-single-story-malay-reserve-bukit-katil-melaka-113337284.htm",
    "https://www.mudah.my/renovated-2-storey-semi-d-au2-keramat-kuala-lumpur-112416987.htm",
    "https://www.mudah.my/6-8-acres-ampang-city-land-for-sale-107961130.htm",
    "https://www.mudah.my/7-roi-jalan-tun-razak-kl-freehold-28-storey-office-tower-building-107587971.htm",
    "https://www.mudah.my/residential-land-for-sale-at-puncak-jalil-selangor-107402936.htm"
]

async def submit_jobs(session, urls):
    print(f"Submitting {len(urls)} jobs...")
    async with session.post(f"{API_URL}/listings/scrape", json={"urls": urls}) as resp:
        if resp.status != 202:
            print(f"Failed to submit jobs: {await resp.text()}")
            return []
        data = await resp.json()
        return data.get("task_ids", [])

async def check_status(session, task_ids):
    async with session.post(f"{API_URL}/listings/scrape/status", json=task_ids) as resp:
        if resp.status != 200:
            print(f"Failed to check status: {await resp.text()}")
            return {}
        return await resp.json()

async def main():
    async with aiohttp.ClientSession() as session:
        # 1. Submit a batch of jobs
        # Let's submit 50 jobs to see if concurrency handles it better than 3 at a time.
        batch_urls = URLS[:50]
        task_ids = await submit_jobs(session, batch_urls)
        
        if not task_ids:
            print("No task IDs received.")
            sys.exit(1) # Exit with error code
            return

        print(f"Submitted {len(task_ids)} tasks. Monitoring progress...")
        
        start_time = time.time()
        while True:
            statuses = await check_status(session, task_ids)
            
            complete = 0
            in_progress = 0
            queued = 0
            not_found = 0
            
            for tid, info in statuses.items():
                s = info.get("status")
                if s == "complete":
                    complete += 1
                elif s == "in_progress":
                    in_progress += 1
                elif s == "queued":
                    queued += 1
                else:
                    not_found += 1
            
            elapsed = time.time() - start_time
            print(f"[{elapsed:.1f}s] Completed: {complete}, In Progress: {in_progress}, Queued: {queued}, Other: {not_found}")
            
            if complete == len(task_ids):
                print("All tasks completed!")
                sys.exit(0) # Exit with success code
                break
            
            if elapsed > 300: # 5 minutes timeout
                print("Timeout reached.")
                sys.exit(1) # Exit with error code
                break
                
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
