# Jenkins Exporter

[![Build Status](https://api.travis-ci.org/lovoo/jenkins_exporter.svg?branch=travis_setup)](https://travis-ci.org/lovoo/jenkins_exporter)

Jenkins exporter for prometheus.io, written in python.

This exporter is based on Robust Perception's python exporter example:
For more information see (http://www.robustperception.io/writing-a-jenkins-exporter-in-python)

## Usage

    jenkins_exporter.py [-h] [-j jenkins] [--user user] [-k]
                        [--password password] [-p port]

    optional arguments:
      -h, --help            show this help message and exit
      -j jenkins, --jenkins jenkins
                            server url from the jenkins api
      --user user           jenkins api user
      --password password   jenkins api password
      -p port, --port port  Listen to this port
      -k, --insecure        Allow connection to insecure Jenkins API

#### Example

    docker run -d -p 9118:9118 pipedrive/jenkins_exporter:latest

## Installation

    git clone git@github.com:pipedrive/jenkins_exporter.git
    cd jenkins_exporter
    pip install -r requirements.txt

