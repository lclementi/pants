# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from pants_test.base_test import BaseTest


class MavenLayoutTest(BaseTest):
  def setUp(self):
    super(MavenLayoutTest, self).setUp()

    self.add_to_build_file('projectB/src/main/scala',
                          'scala_library(name="test", sources=[])')
    self.create_file('projectB/BUILD', 'maven_layout()')

    self.add_to_build_file('projectA/subproject/src/main/java',
                          'java_library(name="test", sources=[])')
    self.create_file('BUILD', 'maven_layout("projectA/subproject")')

  def test_layout_here(self):
    self.assertEqual('projectB/src/main/scala',
                     self.target('projectB/src/main/scala:test').target_base)

  def test_subproject_layout(self):
    self.assertEqual('projectA/subproject/src/main/java',
                     self.target('projectA/subproject/src/main/java:test').target_base)