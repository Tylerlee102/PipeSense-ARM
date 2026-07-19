FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      make \
      g++ \
      cmake \
      python3 \
      python3-pip \
      iverilog \
      verilator \
      yosys \
      nextpnr-ecp5 \
      gcc-riscv64-unknown-elf \
      binutils-riscv64-unknown-elf \
      libelf-dev \
      libboost-regex-dev \
      libboost-system-dev \
      device-tree-compiler \
      srecord \
      z3 \
      cvc4 && \
    rm -rf /var/lib/apt/lists/*

ARG SBY_COMMIT=fea6e467d067b3ea84b6b5ac08cd48beb59f0d42
RUN git clone https://github.com/YosysHQ/sby.git /tmp/sby && \
    cd /tmp/sby && \
    git checkout "$SBY_COMMIT" && \
    make install PREFIX=/usr/local && \
    rm -rf /tmp/sby

RUN for tool in gcc g++ ar as ld nm objcopy objdump ranlib readelf size strings strip; do \
      ln -s "/usr/bin/riscv64-unknown-elf-${tool}" "/usr/local/bin/riscv32-unknown-elf-${tool}"; \
    done

ARG SPIKE_COMMIT=907862288f7b2af1afe533a4c74a5f33cc851830
RUN git clone --filter=blob:none https://github.com/riscv-software-src/riscv-isa-sim.git /tmp/spike && \
    cd /tmp/spike && \
    git checkout "$SPIKE_COMMIT" && \
    mkdir build && cd build && \
    ../configure --prefix=/usr/local && \
    make -j2 && make install && \
    rm -rf /tmp/spike

ARG SV2V_VERSION=v0.0.13
ARG SV2V_SHA256=552799a1d76cd177b9b4cc63a3e77823a3d2a6eb4ec006569288abeff28e1ff8
RUN python3 -c "import hashlib,urllib.request,zipfile; from pathlib import Path; p=Path('/tmp/sv2v.zip'); p.write_bytes(urllib.request.urlopen('https://github.com/zachjs/sv2v/releases/download/${SV2V_VERSION}/sv2v-Linux.zip').read()); assert hashlib.sha256(p.read_bytes()).hexdigest() == '${SV2V_SHA256}'; zipfile.ZipFile(p).extractall('/tmp/sv2v')" && \
    install -m 0755 /tmp/sv2v/sv2v-Linux/sv2v /usr/local/bin/sv2v && \
    rm -rf /tmp/sv2v /tmp/sv2v.zip

WORKDIR /workspace
COPY . /workspace

RUN python3 -m pip install --break-system-packages -r requirements.txt fusesoc==2.4.3 scons==4.8.1
RUN python3 scripts/check_artifact.py

CMD ["python3", "scripts/run_sim.py"]
