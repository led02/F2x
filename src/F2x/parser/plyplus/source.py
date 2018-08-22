'''
Created on 12.02.2016

@author: meinel
'''
import logging
import os
import re
import sys
import time

import plyplus

from F2x.parser import source
from F2x.parser.plyplus import tree


log = logging.getLogger(__name__)
grammar_cache = {}
package_path, _ = os.path.split(__file__)


def load_grammar(grammar_filename):
    if grammar_filename[0] == u'@':
        # Replace '@'-prefix with path to F2x.grammar.
        grammar_filename = os.path.join(package_path, u'grammar', grammar_filename[1:])

    # Need to adjust recursion limit as plyplus is very recusive and FORTRAN grammars are complex.
    old_recursionlimit = sys.getrecursionlimit()
    sys.setrecursionlimit(3000)

    log.info(u"Loading grammar from {0}. This may take some time...".format(grammar_filename))

    start = time.time()
    grammar_file = open(grammar_filename, 'r')
    grammar = plyplus.Grammar(grammar_file)
    grammar_cache[grammar_filename] = grammar
    timer = time.time() - start
    
    log.debug(u"* Loaded grammar in {0}.".format(timer))
    sys.setrecursionlimit(old_recursionlimit)

    return grammar


class SourceFile(source.SourceFile):
    def parse(self):
        grammar_filename = self.config.get('parser', 'grammar')

        if grammar_filename in grammar_cache:
            grammar = grammar_cache[grammar_filename]
        else:
            grammar = load_grammar(grammar_filename)

        self.tree = grammar.parse(self.source)

    def get_gtree(self):
        module = tree.Module(self.tree)
        module.export_methods(self.config)
        return module
