# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from textwrap import dedent

from pants_test.base_test import BaseTest


class BundleTest(BaseTest):

  def test_bundle_filemap_dest_bypath(self):
    self.create_dir('src/java/org/archimedes/buoyancy/config')
    self.create_file('src/java/org/archimedes/buoyancy/config/densities.xml')
    self.add_to_build_file('src/java/org/archimedes/buoyancy/BUILD', dedent('''
      jvm_binary(name='unused')
    '''))
    self.add_to_build_file('src/java/org/archimedes/buoyancy/BUILD', dedent('''
      jvm_app(name='buoyancy',
        dependencies=[':unused'],
        bundles=[
          bundle()
            .add('config/densities.xml')
        ]
      )
    '''))
    app = self.target('src/java/org/archimedes/buoyancy')
    # after one big refactor, ../../../../../ snuck into this path:
    self.assertEquals(app.bundles[0].filemap.values()[0],
                      'config/densities.xml')

  def test_bundle_filemap_dest_byglobs(self):
    self.create_dir('src/java/org/archimedes/tub/config')
    self.create_file('src/java/org/archimedes/tub/config/one.xml')
    self.create_file('src/java/org/archimedes/tub/config/two.xml')
    self.add_to_build_file('src/java/org/archimedes/tub/BUILD', dedent('''
      jvm_binary(name='unused')
    '''))
    self.add_to_build_file('src/java/org/archimedes/tub/BUILD', dedent('''
      jvm_app(name='tub',
        dependencies=[':unused'],
        bundles=[
          bundle()
            .add(globs('config/*.xml'))
        ]
      )
    '''))
    app = self.target('src/java/org/archimedes/tub')
    for k in app.bundles[0].filemap.keys():
      if k.endswith('archimedes/tub/config/one.xml'):
        onexml_key = k
    self.assertEquals(app.bundles[0].filemap[onexml_key],
                      'config/one.xml')

  def test_bundle_filemap_dest_relative(self):
    self.create_dir('src/java/org/archimedes/crown/gold/config')
    self.create_file('src/java/org/archimedes/crown/gold/config/five.xml')
    self.add_to_build_file('src/java/org/archimedes/crown/BUILD', dedent('''
      jvm_binary(name='unused')
    '''))
    self.add_to_build_file('src/java/org/archimedes/crown/BUILD', dedent('''
      jvm_app(name='crown',
        dependencies=[':unused'],
        bundles=[
          bundle(relative_to='gold')
            .add('gold/config/five.xml')
        ]
      )
    '''))
    app = self.target('src/java/org/archimedes/crown')
    for k in app.bundles[0].filemap.keys():
      if k.endswith('archimedes/crown/gold/config/five.xml'):
        fivexml_key = k
    self.assertEquals(app.bundles[0].filemap.values()[0],
                      'config/five.xml')

  def test_bundle_add_add(self):
    self.create_dir('src/java/org/archimedes/volume/config/stone')
    self.create_file('src/java/org/archimedes/volume/config/stone/dense.xml')
    self.create_dir('src/java/org/archimedes/volume/config')
    self.create_file('src/java/org/archimedes/volume/config/metal/dense.xml')
    self.add_to_build_file('src/java/org/archimedes/volume/BUILD', dedent('''
      jvm_binary(name='unused')
    '''))
    self.add_to_build_file('src/java/org/archimedes/volume/BUILD', dedent('''
      jvm_app(name='volume',
        dependencies=[':unused'],
        bundles=[
          bundle(relative_to='config')
            .add('config/stone/dense.xml')
            .add('config/metal/dense.xml')
        ]
      )
    '''))
    app = self.target('src/java/org/archimedes/volume')
    for k in app.bundles[0].filemap.keys():
      if k.endswith('archimedes/volume/config/stone/dense.xml'):
        stonexml_key = k
    self.assertEquals(app.bundles[0].filemap[stonexml_key],
                      'stone/dense.xml')