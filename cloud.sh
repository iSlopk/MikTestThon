#!/usr/bin/env bash

cat <<'EOF'
---------------------------------------
Installing Mikthon is in progress..                                                  
---------------------------------------                                                  


                                                  
Copyright (C) 2020-2025 by iSlopk@Github, < https://github.com/iSlopk >.
This file is part of < https://github.com/iSlopk/Mikthon > project,
and is released under the "GNU v3.0 License Agreement".
Please see < https://github.com/iSlopk/Mikthon/blob/main/LICENSE >
All rights reserved.
EOF

gunicorn app:app --daemon && python -m Mikthon
