FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      make \
      python3 \
      python3-pip \
      iverilog \
      yosys \
      z3 \
      cvc4 && \
    rm -rf /var/lib/apt/lists/*

ARG SBY_COMMIT=fea6e467d067b3ea84b6b5ac08cd48beb59f0d42
RUN git clone https://github.com/YosysHQ/sby.git /tmp/sby && \
    cd /tmp/sby && \
    git checkout "$SBY_COMMIT" && \
    make install PREFIX=/usr/local && \
    rm -rf /tmp/sby

WORKDIR /workspace
COPY . /workspace

RUN python3 -m pip install --break-system-packages -r requirements.txt
RUN python3 scripts/check_artifact.py

CMD ["python3", "scripts/run_sim.py"]
