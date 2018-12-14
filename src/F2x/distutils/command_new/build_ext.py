# -*- encoding: utf-8 -*-
#
# Copyright 2018 German Aerospace Center (DLR)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.build_src
import os

from numpy.distutils.command.build_ext import build_ext as numpy_build_ext
from numpy.distutils.command import build_clib

from F2x.distutils.strategy import get_strategy, base


class build_ext(numpy_build_ext):
    def initialize_options(self):
        super(build_ext, self).initialize_options()
        self.strategy = None

    def finalize_options(self):
        super(build_ext, self).finalize_options()

        if self.strategy is not None:
            self.strategy = get_strategy(self.strategy)
        else:
            self.strategy = base.BuildStrategy()

    def build_extension(self, ext):
        old_strategy, self.strategy = self.strategy, ext.strategy
        ext.strategy.prepare_build_extension(self, ext)
        super(build_ext, self).build_extension(ext)
        ext.strategy.finish_build_extension(self, ext)
        self.strategy = old_strategy

    def get_ext_filename(self, ext_name):
        *package_path, ext_name = ext_name.split('.')
        filename = self.strategy.get_ext_filename(self, ext_name)
        if filename is None:
            filename = super(build_ext, self).get_ext_filename(ext_name)
        return os.path.join(*package_path, filename)
