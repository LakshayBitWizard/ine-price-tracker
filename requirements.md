INE | Software Engineer Intern Assignment 
Assignment: Product Price Tracker (Web Scraping) 
Important Instructions 
● Strictly follow submission guidelines - any violation will result in disqualification. 
● Zero tolerance for plagiarism or cheating - all suspected cases will be rejected 
immediately. 
● Send your resume only if you can complete the assignment at least partially. 
● You may be asked to modify your submitted code live during a video interview. 
● No additional clarifications will be given. Interpret and implement the requirements 
independently. 
● Focus on completing all base features first. A more complete, functional solution 
significantly improves your selection chances. 
Objective: INE provides a hosted mock storefront for this assignment. Your task is to build a 
small web application that lets a user pick a product from that store and then tracks its price 
over time by scraping the store on a schedule. Any other information about the products may 
also be provided on your dashboard. The store is deliberately awkward to scrape, and getting 
the scraping to work reliably is the heart of this assignment, not the interface around it. What 
matters is that the scraper keeps working correctly over many unattended runs. 
 
Build a small full-stack web application where users can: 
1. Search for and pick a product from INE's hosted mock store, by partial or full product 
name. 
2. Track that product, so the app scrapes its current price and stock on a fixed schedule. 
3. View the product's price and stock history over time as a chart or table. 
4. See a per-product scrape log showing each scrape attempt and its outcome. 
The storefront to scrape can be found at https://demo.inelabteamdev.com/ 
 
 
 
Tech Stack: 
● Frontend: React.js or Vue.js, deployed on Vercel 
● Backend: Node.js (Express) or Django, deployed on Render 
● Database: Supabase (PostgreSQL) for tracked products and price history 
● Scraping: your choice of lightweight HTTP fetching with HTML parsing, or a headless 
browser (Playwright or Puppeteer) where the page genuinely requires JavaScript 
rendering 
● Scheduling: an external cron service (for example cron-job.org) or a scheduled function, 
since free-tier backends sleep 
Core Features: 
● Product Selection 
○ Users search INE's hosted mock store by partial or full product name and pick a 
product to track. Persist tracked products in Supabase. 
● Scheduled Scraping (the core challenge) 
○ The app scrapes each tracked product's current price and stock from the mock 
store on a fixed schedule of once every 2 hours. The mock store is intentionally 
difficult: prices change frequently, some content loads asynchronously after a 
short delay, and responses are occasionally slow or return errors. Your scraper 
must be reliable across many unattended runs. Handle slow and failed loads with 
retries, recover when a request errors or a page shifts, and never silently stop or 
store incorrect data. Because free-tier backends sleep, trigger scheduled scrapes 
via an external cron service or a scheduled function rather than an always-on 
loop. Prefer lightweight HTTP fetching and HTML parsing where possible. Reach 
for a headless browser only where the page genuinely requires it. 
● Price History and Scrape Log 
○ Show each tracked product's price and stock over time as a chart or table. Show 
a per-product scrape log listing every scrape attempt with a timestamp and its 
outcome (success, retried, or failed). Failures must be recorded honestly, not 
hidden. You may also display extra information about the product on your 
dashboard according to your judgement.  
● Observable (Headed) Run 
● Provide a way to run the scraper in headed mode so its behavior can be watched. 
Submit a short screen recording of a headed run against the mock store, 
including how the scraper handles a slow or failing response. 
Deliverables: 
● A link to the hosted, live site. 
● Public GitHub repository URL containing all the source files. 
● A short screen recording (2 to 4 minutes) of the scraper running in headed mode against 
the mock store, showing how it handles slow or failing responses. 
● A README with setup instructions, the scraping schedule, and the environment variables 
required. 
● A short design note explaining how you made the scraping reliable, what trade-offs you 
made, and what your AI tools got wrong on the first attempt and how you corrected it. 
● PDF resume. 
 
Evaluation Criteria: 
● Scraping Reliability: the scraper keeps working across many unattended runs, with 
retries and graceful failure handling. This is the core of the assessment. 
● Correctness under Difficulty: it extracts the right price and stock even when content 
loads late or a response is slow, and it never stores wrong or empty data on failure. 
● Honest History and Logging: the price history and scrape log accurately reflect what 
happened, including failures. 
● Judgment: a sensible choice between lightweight fetching and a headless browser, and 
correct handling of the free-tier scheduling constraint. 
● Deployment: frontend on Vercel, backend on Render, data on Supabase, reachable from 
the live link. 
Bonus: 
● Price-drop or back-in-stock alerts, in-app or by email via SendGrid. 
● A dashboard across multiple tracked products or extra information about tracked 
products. 
● Change detection that flags when the store's page structure changes. 
● Configurable scrape frequency per product. 
● CI/CD with GitHub Actions. 
 
Submission: 
● Email: to sstephen@ine.com cc ssingh@ine.com  
● Subject: First Round: Software Engineer Intern Assignment - <Your Name> 
● Deadline: September 20, 2026 (Sunday) - 11:59PM IST 
 
 
Resources (Only Free Tiers): 
● Frontend Hosting: Vercel 
● Backend Hosting: Render.com 
● Database: Supabase (PostgreSQL) 
● Scheduled Scrape Triggers (Cron Jobs): cron-job.org 
● Headless Browser (if needed): Playwright or Puppeteer 
● Mock Store (target site): https://demo.inelabteamdev.com  
Note: 
● Free-tier instances may automatically go idle or sleep. Trigger scrapes via an external 
cron service rather than an always-on process, and keep the instance warm if needed. 
● Scrape only INE's provided mock store. Do not scrape real retailers or third-party sites. 