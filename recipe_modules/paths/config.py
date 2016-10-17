# Copyright 2016 The Fuchsia Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['path'].CONFIG_CTX


@CONFIG_CTX()
def common(c):
    c.dynamic_paths['checkout'] = None


@CONFIG_CTX(includes=['common'])
def swarmbucket(c):
    c.base_paths['root'] = c.CURRENT_WORKING_DIR[:-4]
    c.base_paths['slave_build'] = c.CURRENT_WORKING_DIR
    c.base_paths['cache'] = c.base_paths['root'] + ('cache',)
    c.base_paths['git_cache'] = c.base_paths['root'] + ('git_cache',)
    c.base_paths['goma_cache'] = c.base_paths['root'] + ('goma_cache',)