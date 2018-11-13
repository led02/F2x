import configparser
import os
from distutils.sysconfig import get_config_vars as distuils_get_config_vars

from F2x.distutils.strategy.extension import ExtensionBuildStrategy


class ExtensionLibBuildStrategy(ExtensionBuildStrategy):
    def get_ext_filename(self, build_src, extension):
        library_name = build_src.find_library_name(extension)
        suffix = distuils_get_config_vars('SHLIB_SUFFIX')[0]
        package_path = build_src.get_ext_fullname(extension.name).split('.')[:-1]

        return os.path.join(*package_path, f'lib{library_name}{suffix}')

    def finish_wrapper_input(self, build_src, extension, f2x_input):
        build_ext = build_src.get_finalized_command('build_ext')
        f2x_input = super(ExtensionLibBuildStrategy, self).finish_wrapper_input(build_ext, extension, f2x_input)

        # Ensure to load the correct library.
        for target_file, f2x_info, extensions in f2x_input:
            if 'config' not in f2x_info:
                f2x_info['config'] = configparser.RawConfigParser()

            library_file_name = build_ext.get_ext_filename(build_ext.get_ext_fullname(extension.name))

            config = f2x_info.get('config')
            if not config.has_section('generate'):
                config.add_section('generate')

            config.set('generate', 'dll', os.path.basename(library_file_name))
            with open(target_file + '-wrap', 'w') as wrapper_file:
                config.write(wrapper_file)

        return f2x_input