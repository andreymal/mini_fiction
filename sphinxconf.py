#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os


root = os.path.dirname(__file__)
sphinx_root = open(os.path.join(root, 'sphinxroot.txt'), 'rb').read().strip().decode('utf-8')

local_path = os.path.join(root, 'local_sphinx.conf')
print(open(local_path, 'rb').read().decode('utf-8').replace('%SPHINXROOT%', sphinx_root))

print(open(os.path.join(root, 'sphinx.conf'), 'rb').read().decode('utf-8').replace('%SPHINXROOT%', sphinx_root))
