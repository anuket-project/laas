# Lab as a Service (LaaS)

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/anuket-project/laas/badge)](https://scorecard.dev/viewer/?uri=github.com/anuket-project/laas)

## Overview

The Lab as a Service (LaaS) project aims to improve development, testing, and integration work in Anuket and the Linux Foundation Networking community by providing customizable hardware environments, or “labs”, to developers. Deploying and testing Anuket requires large amounts of baremetal hardware which is usually not available to developers.

LaaS as a project is composed of the web portal that users interact with, as well as an API that the web portal provides for participating labs. Labs that want to participate in LaaS must host hardware and consume the web portal's API in order to configure and manage that hardware.

For more details, please check see https://lf-anuket.atlassian.net/wiki/spaces/HOME/pages/21861157/Lab+as+a+Service


## This Repository
This repository contains code for a reference LaaS dashboard. It must be used alongside a custom backend. The reference backend can be found at [laas-reflab](https://github.com/anuket-project/laas-reflab).

This is largely maintained by the UNH-IOL, but bug fixes and features are welcome from the community.

## Starting a local deployment using docker and docker compose
1. Install docker and docker compose
1. Copy `config.env.sample` to `config.env` and update fields as needed.
1. Run `make dev-up` to build and run a local dashboard

Note: You will need to also run a local backend to access most features of LaaS.

## History
- Development history of the project before 2023.10.26
  - Code: https://gerrit.opnfv.org/gerrit/gitweb?p=laas.git;a=summary
  - Reviews: https://gerrit.opnfv.org/gerrit/q/project:laas


## License & Copyright 

Copyright (c) 2016 Max Breitenfeldt and others

All rights reserved. This program and the accompanying materials
are made available under the terms of the Apache License, Version 2.0
which accompanies this distribution, and is available at
http://www.apache.org/licenses/LICENSE-2.0