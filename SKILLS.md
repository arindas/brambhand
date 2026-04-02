# SKILLS

## Agent Memory

Memory system to keep track of project work progress.

```
.agent/
└── memory
    ├── 0-memory-summary.md
    └── entry-0000000000.md
    ... more entries ...
```

`0-memory-summary.md` keeps a running summary.

`entry-N.md` logs individual memory entiries. Each memory entry is prefaced with a set of tags to faciliate searching
Memory compaction happens every 10 entries into the running summary. So working memory should be summary and last
10 entries with optional tag based keyword search or regular search for looking up specific entries


## Web search

Use `bash` `curl` on google for searching the web. Filter out relevant items by title.
Use the `man` command to know more about `curl`.

Follow links by opening the search result URL with curl.

When a web page result is fetched, look for a table of contents to look for relevant items.
Then only read the relevant section from the file.


## PDF search

Use `bash` `pdftotext` to extract text from PDFs. 
Use the `man` command to know more about `pdftotext`.

Important dont extract all the text at once. Look for a table of contents. 
Then lookup the exact section. Keep in mind the page offsets to account for
preface and other items preceding the numbered pages.


## Offline knowledge base

There is a commputer on the local network reachable via SSH that contains a lot of pdf files.

```bash
ssh arindas@192.168.1.2

# goto directory containiing ebooks on the SSH remote computer
cd ebooks

# files are organized by:
# <discipline>/<subtopic>/<specialization or document type>/<document>

```

Use the PDF search SKILL to search for relevant information.
