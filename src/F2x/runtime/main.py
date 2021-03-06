# -*- coding: utf-8 -*-
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
# limitations under the License.
""" Main program for F2x - A versatile, template based FORTRAN wrapper.
"""
import warnings

warnings.simplefilter('ignore', ResourceWarning)

import importlib
import os
import sys
import time
from configparser import ConfigParser

import jinja2
import plyplus

import F2x
from F2x.parser.plyplus import source
from F2x.runtime import argp
from F2x.template import get_template, register_template, package_dir as template_package_dir


IGNORE_DELTA = 3


def _load_templates(log, templates, template_path=None):
    log.info(u"Loading {0} templates...".format(len(templates)))
    loaded_templates = []
    template_path = list(template_path or [])

    start = time.time()
    for mod, filename, filepath, suffix in templates:
        log.debug(u"* Loading template from {0}...".format(filename))
        template_loader = jinja2.FileSystemLoader(template_path)
        template_env = jinja2.Environment(loader=template_loader, extensions=['jinja2.ext.do'])

        try:
            template = template_loader.load(template_env, filename)
        except IOError:
            with open(filepath, 'r') as template_file:
                template = template_env.from_string(template_file.read())
        loaded_templates.append((template, suffix))
    
    timer = time.time() - start
    log.debug(u"* Loaded {0} templates in {1}.".format(len(templates), timer))
    return loaded_templates


def _templates_from_args(log, args):
    strategy = None
    template_path = args.template_path or []
    templates = []

    if args.wrap:
        # Load strategy and build extension
        from F2x.distutils.strategy import get_strategy
        strategy = get_strategy(args.wrap)

        if not args.template:
            for name in strategy.templates:
                module = get_template(name)
                if module is None:
                    continue

                for filename in module.templates or []:
                    filepath = os.path.join(module.package_dir, filename)
                    suffix, _ = os.path.splitext(os.path.basename(filename))
                    templates.append((module, filename, filepath, suffix))

    if args.template:
        # If templates are supplied, process them
        for filename in args.template:
            try:
                if filename[0] == u'@':
                    filename = filename[1:]
                    filepath = os.path.join(template_package_dir, filename)
                    template_path.append(os.path.dirname(filepath))

                    modpath, *_, basename = os.path.split(filename)
                    suffix, _ = os.path.splitext(basename)
                    module = get_template(modpath)

                else:
                    filepath = filename
                    basename, ext = os.path.splitext(filename)
                    suffix = os.path.basename(basename)

                    # Template without extension is most probably a built-in so we can (try to) load it
                    if not ext:
                        module = get_template(basename)
                    else:
                        module = None

                templates.append((module, filename, filepath, suffix))

            except ImportError:
                log.warn(f'could not load template "{filename}" as {modpath}.')
                continue

    return templates, template_path, strategy


def _get_file_list(args):
    templates, _, _ = _templates_from_args(None, args)
    all = []
    filelist = lambda d, l: map(lambda f: os.path.join(d, f), l)

    for what in args.get:
        if what == 'extlib':
            ext = _make_extension(args)
            ext.strategy.prepare_extension(None, ext)
            extlib_name = ext.strategy.get_ext_filename(None, args.library_name or ext.name)

            if extlib_name:
                all.append(extlib_name)

        else:
            for mod, _, _, _ in templates:
                if what == 'libraries':
                    for _, info in mod.libraries or []:
                        all.extend(filelist(mod.package_dir, info.get('sources', [])))

                else:
                    all.extend(filelist(mod.package_dir, getattr(mod, what, []) or []))

    print(' '.join(all))



def main(argv=None, from_distutils=False):
    # Parse command line
    args = argp.parse_args(argv)

    # Load configuration if assigned
    config = ConfigParser()
    if args.config:
        config.read(args.config)

        # HACK Store config values in args...
        args.grammar = argp.get_arg(args, config, 'grammar', 'parser', "@fortran.g", str)
        args.config_suffix = argp.get_arg(args, config, 'config_suffix', 'parser', "-wrap", str)
        args.output_pre = argp.get_arg(args, config, 'output_pre', 'parser', False, bool)
        args.configure = argp.get_arg(args, config, 'configure', 'parser', False, bool)
        args.encoding = argp.get_arg(args, config, 'encoding', 'parser', 'utf8', str)
        args.tree_class = argp.get_arg(args, config, 'tree_class', 'parser', None, str)

        args.wrap = argp.get_arg(args, config, 'wrap', 'wrap', None, str)
        args.module_name = argp.get_arg(args, config, 'module_name', 'wrap', None, str)
        args.library_name = argp.get_arg(args, config, 'library_name', 'wrap', None, str)
        args.autosplit = argp.get_arg(args, config, 'autosplit', 'wrap', False, str)
        args.add_strategy = argp.get_arg(args, config, 'add_strategy', 'wrap', [], lambda e: map(lambda s: s.split(','), e.split(';')))

        args.register_template = argp.get_arg(args, config, 'register_template', 'generate', [], lambda p: p.split(';'))
        args.template = argp.get_arg(args, config, 'template', 'generate', [], lambda t: t.split(';'))
        args.template_path = argp.get_arg(args, config, 'template_path', 'generate', [], lambda p: p.split(';'))
        args.jinja_ext = argp.get_arg(args, config, 'jinja_ext', 'generate', ['jinja2.ext.do'], lambda e: e.split(';'))

        args.logfile = argp.get_arg(args, config, 'logfile', 'logging', None, str)
        # HACK end

    # Shortcut if action modus is "get" (i.e., output library files)
    if args.get:
        _get_file_list(args)
        sys.exit(0)

    # Decide which log to use
    if not from_distutils:
        log = argp.init_logger(args)
        log.info(f"{F2x.program_name} Version {F2x.get_version_string()}")

    for template_package in args.register_template or []:
        if '.' in template_package:
            template_package, package_name = template_package.rsplit('.', 1)
        else:
            template_package, package_name = None, template_package

        module = importlib.import_module(((template_package + '.') if template_package is not None else '') + package_name, template_package)
        register_template(module)

    # Register strategies
    if args.add_strategy:
        from F2x.distutils import strategy

        for name, cls_name, templates in args.add_strategy:
            cls_package, cls_module, cls_name = cls_name.rsplit('.', 2)
            module = importlib.import_module(cls_package + '.' + cls_module, cls_package)
            cls = getattr(module, cls_name)
            strategy.register_strategy(name, cls(templates.split(',')))

    if args.wrap:
        # If a strategy is given, load it and build extension
        from F2x.distutils import core

        # Enforce 'inplace' build for command line call
        sys.argv = sys.argv[:1] + ['build_ext', '--inplace']
        if args.force:
            sys.argv.append('--force')

        # Build the extension
        ext = _make_extension(args)
        core.setup(ext_modules=[ext])

    else:
        # Run actual wrapper
        from F2x.runtime.wrapper import F2xWrapper

        wrapper = F2xWrapper(args, log)
        wrapper.run()


def _make_extension(args):
    from F2x.distutils.extension import Extension

    ext = Extension(args.module_name or args.library_name or 'ext.*', args.source,
                    strategy=args.wrap, f2x_options=[], templates=args.template,
                    autosplit=args.autosplit, inline_sources=True)
    return ext


def _run_wrapper(templates, template_path, args, log):
    templates = _load_templates(log, templates, template_path)

    for source_filename in args.source:
        log.info(u"Processing {0}...".format(source_filename))

        src = source.SourceFile(source_filename, args)
        src.read()
        src.preprocess()

        log.debug(u"* Parsing FORTRAN source...")

        try:
            src.parse()

        except plyplus.ParseError as e:
            if args.configure:
                ignore_lines = _ignore_error_lines(e, src)

                print('ignore =')
                for line in ignore_lines:
                    print('\t{0}\t;{1}'.format(line, src.pre_source_lines[line - 1]))

            else:
                for err in e.errors:
                    _print_error(err, source_filename, src)
                    continue

        log.debug(u"* Getting the tree...")

        try:
            module = src.get_gtree()
        except Exception as e:
            log.error(str(e))
            continue

        if not src.config.has_section('generate'):
            src.config.add_section('generate')
        if not src.config.has_option('generate', 'dll'):
            src.config.set('generate', 'dll', 'lib' + module['name'] + '.so')

        output_basename, _ = os.path.splitext(source_filename)

        for template, suffix in templates:
            output_filename = output_basename + suffix
            log.debug(u"* Generating {0}...".format(output_filename))

            output = template.render({
                u'ast': src.tree, u'module': module,
                u'config': src.config, u'ifort_dll': True,
                u'context': {u'filename': source_filename, u'basename': os.path.basename(output_basename),
                             u'args': args}})

            with open(output_filename, 'wb') as output_file:
                output_file.write(output.encode(args.encoding))


def _print_error(err, source_filename, src):
    val = err.args.get('value', '<Not defined>')
    line = err.args.get('line', -1)
    col = err.args.get('col', None)

    if col > 0:
        loc = f'{source_filename}:{line}:{col}:'
    else:
        loc = f'{source_filename}:{line}'

    print(f'{loc}Syntax error near "{val}"')
    if col >= 0:
        space = ''.join([(c if c == '\t' else ' ') for c in src.pre_source_lines[line - 1][:col - 1]])
        print(loc + src.pre_source_lines[line - 1])
        print(loc + space + ('^' * len(val)))


def _ignore_error_lines(e, src):
    ignore_lines = set((err.args['line'] for err in e.errors if 'line' in err.args))
    if src.config.has_option('parser', 'ignore'):
        ignore = src.config.get('parser', 'ignore')
        if '\n' in ignore:
            config_ignore_lines = set(map(int, [line.split(';')[0].rstrip() for line in ignore.splitlines() if line]))
        else:
            config_ignore_lines = set(map(int, map(str.strip, ignore.split(','))))
        ignore_lines = ignore_lines.union(config_ignore_lines)
    index = 0
    ignore_lines = sorted(ignore_lines)
    while index < len(ignore_lines) - 2:
        while index < len(ignore_lines) - 2 \
                and 'END' in src.pre_source_lines[ignore_lines[index] - 1]:
            ignore_lines.pop(index)

        curr = ignore_lines[index]
        succ = ignore_lines[index + 1]
        delta = succ - curr

        if delta < IGNORE_DELTA \
                and 'END' not in src.pre_source_lines[succ - 1]:
            ignore_lines[index + 1:index + 1] = range(curr + 1, succ)
            index += delta

        index += 1
    return ignore_lines


#        if args.copy_glue and not args.py_absolute_import:
#            output_dir, _ = os.path.split(output_basename)
#            output_file = os.path.join(output_dir, "glue.py")
#            if os.path.exists(output_file):
#                os.unlink(output_file)
#            shutil.copy(glue.__file__, output_file)


if __name__ == '__main__':
    main()
