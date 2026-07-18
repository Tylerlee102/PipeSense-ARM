FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      latexmk \
      poppler-utils \
      texlive-fonts-recommended \
      texlive-latex-base \
      texlive-latex-recommended \
      texlive-pictures \
      texlive-publishers && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/paper
