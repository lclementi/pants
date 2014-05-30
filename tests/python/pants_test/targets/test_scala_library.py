# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from textwrap import dedent

from pants_test.base_test import BaseTest


class ScalaLibraryTest(BaseTest):

  def setUp(self):
    super(ScalaLibraryTest, self).setUp()

    self.add_to_build_file('3rdparty', dedent('''
        jar_library(
          name='hub-and-spoke',
          jars=[
            jar('org.jalopy', 'hub-and-spoke', '0.0.1')
          ]
        )
        '''))

    self.add_to_build_file('scala', dedent('''
        scala_library(
          name='lib',
          sources=[],
          java_sources=[
            pants('java:explicit_scala_dep'),
            pants('java:no_scala_dep'),
          ]
        )
        '''))

    self.add_to_build_file('java', dedent('''
        java_library(
          name='explicit_scala_dep',
          sources=[],
          dependencies=[
            pants('scala:lib'),
            pants('3rdparty:hub-and-spoke'),
          ]
        )

        java_library(
          name='no_scala_dep',
          sources=[],
          dependencies=[]
        )
        '''))

    self.lib_hub_and_spoke = self.target('3rdparty:hub-and-spoke')
    self.scala_library = self.target('scala:lib')
    self.java_library_explicit_dep = self.target('java:explicit_scala_dep')
    self.java_library_no_dep = self.target('java:no_scala_dep')

  def test_mixed_linkage(self):
    self.assertEqual(set(self.lib_hub_and_spoke.jar_dependencies),
                     set(self.scala_library.jar_dependencies),
                     'The scala end of a mixed language logical lib should be linked with the java'
                     'code deps excluding itself.')

    self.assertEqual(set(self.scala_library.jar_dependencies),
                     set(self.java_library_explicit_dep.jar_dependencies),
                     'The java end of a mixed language logical lib with an explicit dep should be '
                     'unaffected by linking.')