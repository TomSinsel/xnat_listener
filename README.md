# XNAT Listener & Runner

This repository provides a **listener and runner system** that monitors an XNAT server, retrieves imaging data (e.g. CT scans and RT images), downloads it into local folders, and triggers further processing steps by sending messages to a **RabbitMQ queue**.

---

## 1. XNATlistener

Located in **`xnat_listener.py`**  
Responsible for:

- Connecting to an XNAT server using HTTP Basic Authentication.
- Scanning projects, subjects, and experiments for available data.
- Ensuring that required data types (`xnat:ctScanData`, `xnat:rtImageScanData`) are present.
- Downloading imaging files into structured local directories (`data/{experiment_id}`).
- Skipping experiments that have already been processed.

---

## 2. Runner

Located in **`runner.py`**  
Responsible for:

- Managing already-processed experiment IDs (avoids duplication).
- Calling the `XNATlistener` to fetch new data.
- Sending messages to RabbitMQ once new data is available, enabling the next processing stage in the pipeline.
- Running in two modes:
  - **One-time execution** (`run_once()`)
  - **Continuous polling** (`keep_running(interval=30)`)

---

##  Things to Keep in Mind
- If it is constantly running and it has checked a subject and has has both ct scans and rtstruct, it will not check the subject again eventhough you would change it contents

### XNAT Credentials & URL
- The base url is set for integration into the digione pipeline if you run xnat in a seperate container you need to localhost
```python
listener = XNATlistener(
    username="user",
    password="pass",
    base_url="http://your-xnat-server/data/projects"
)
