# refactor

I want to create an abstracion layer between the intake pipeline, the scraping, and the AI analysis using a queue. The requirements are as follows:

- A new job listing can be submitted to the intake (webhook? firestore entry? something else that fits our architecture better?)
- after intake the listing is parsed and tested to pass our analysis requirements. (stop list, already in the db, etc.)
- if it passes intake requirements, a job-listing scrape job will be created, this will:
  - A: see if the listed company exists in the db, if it does not the company will be scraped, and a company entry will be made in firestore, and a company AI analysis job will be created.
  - B: scrape the job listing to gather as much data as possible, then crate a job-lising AI analysis job.
- A new company can also enter the intake pipeline, if the company does not exist in firestore a company scrape job will immediately be created with the same flow as A above - scrape for data then create an AI analysis job.
  - when a new company is scraped and analyzed we will try to find the company job board, which chould be added as a source, as well as all other applicable data.
- the end result of a job AI analysis will be a job-application entry to be reviewed in the portfolio project.
- we want to guarantee that a job analysis does not happen until the company has already been analyzed.
- the existing source scraping pipeline will dump all found jobs into the intake pipeline for filtering and analysis.

fufure considerations:
 - more intake sources - gmail?
 - alerting on perfect match jobs
