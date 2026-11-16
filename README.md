# small-cap news study

Scripts for a small pilot study of whether public news moves US small-cap stock prices.

- pilot.py: SEC 8-K event study plus a Google News RSS headline pilot
- build_cls_input.py, cls_check.py, prompts/: LLM headline classification and its validator
- restudy_cls.py: joins classifications to abnormal returns
- fetch.py, search.py: parallel page fetcher and multi-source search

Setup: put a contact user-agent string required by SEC fair-access rules in ~/.sec_ua.
Method notes: abnormal return = stock minus IWM, firm-cluster bootstrap CIs, placebo tests.
Results are exploratory and small-sample.
