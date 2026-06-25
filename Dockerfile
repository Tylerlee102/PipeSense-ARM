FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      make \
      python3 \
      python3-pip \
      iverilog \
      yosys && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY . /workspace

RUN python3 -m pip install --break-system-packages -r requirements.txt
RUN python3 scripts/check_artifact.py

CMD ["python3", "scripts/run_sim.py"]
