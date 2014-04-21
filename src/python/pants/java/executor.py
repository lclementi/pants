# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
import subprocess
from abc import abstractmethod, abstractproperty
from contextlib import contextmanager

from twitter.common import log
from twitter.common.collections import maybe_list
from twitter.common.contextutil import environment_as, temporary_file_path
from twitter.common.lang import AbstractClass, Compatibility

from pants.java.distribution import Distribution
from pants.java.jar import Manifest, open_jar


class Executor(AbstractClass):
  """Executes java programs."""

  @staticmethod
  def _scrub_args(classpath, main, jvm_options, args):
    classpath = maybe_list(classpath)
    if not isinstance(main, Compatibility.string) or not main:
      raise ValueError('A non-empty main classname is required, given: %s' % main)
    jvm_options = maybe_list(jvm_options or ())
    args = maybe_list(args or ())
    return classpath, main, jvm_options, args

  class Error(Exception):
    """Indicates an error launching a java program."""

  class Runner(object):
    """A re-usable executor that can run a configured java command line."""

    @abstractproperty
    def executor(self):
      """Returns the executor this runner uses to run itself."""

    @abstractproperty
    def cmd(self):
      """Returns a string representation of the command that will be run."""

    @abstractmethod
    def run(self, stdout=None, stderr=None):
      """Runs the configured java command.

      If there is a problem executing tha java program subclasses should raise Executor.Error.
      Its guaranteed that all arguments are valid as documented in `execute`

      :param stdout: An optional stream to pump stdout to; defaults to `sys.stdout`.
      :param stderr: An optional stream to pump stderr to; defaults to `sys.stderr`.
      """

  def __init__(self, distribution=None):
    """Constructs an Executor that can be used to launch java programs.

    :param distribution: an optional validated java distribution to use when launching java
      programs
    """
    if distribution:
      if not isinstance(distribution, Distribution):
        raise ValueError('A valid distribution is required, given: %s' % distribution)
      distribution.validate()
    else:
      distribution = Distribution.cached()

    self._distribution = distribution

  @contextmanager
  def runner(self, classpath, main, jvm_options=None, args=None):
    """Returns an `Executor.Runner` for the given java command."""
    with self._get_minimized_jar_classpath(classpath) as minimized_classpath:
      yield self._runner(*self._scrub_args(minimized_classpath, main, jvm_options, args))

  def execute(self, classpath, main, jvm_options=None, args=None, stdout=None, stderr=None):
    """Launches the java program defined by the classpath and main.

    :param list classpath: the classpath for the java program
    :param string main: the fully qualified class name of the java program's entry point
    :param list jvm_options: an optional sequence of options for the underlying jvm
    :param list args: an optional sequence of args to pass to the java program

    Returns the exit code of the java program.
    Raises Executor.Error if there was a problem launching java itself.
    """
    executor = self.runner(classpath=classpath, main=main, jvm_options=jvm_options, args=args)
    return executor.run(stdout=stdout, stderr=stderr)

  @abstractmethod
  def _runner(self, classpath, main, jvm_options, args):
    """Subclasses should return a `Runner` that can execute the given java main."""

  def _create_command(self, classpath, main, jvm_options, args):
    cmd = [self._distribution.java]
    cmd.extend(jvm_options)
    cmd.extend(['-cp', os.pathsep.join(classpath), main])
    cmd.extend(args)
    return cmd

  @staticmethod
  @contextmanager
  def _get_minimized_jar_classpath(classpath):
    """
    Classpaths need to be minimized since pants can pass too many command line arguments to java if
    the classpath is too large. This function alleviates this problem by placing all of the jars in
    the classpath into one single JAR.
    """

    jar_classpath = []
    non_jar_classpath = []
    for path in classpath:
      if path.endswith('.jar'):
        jar_classpath.append(path)
      else:
        non_jar_classpath.append(path)

    manifest = Manifest()
    manifest.addentry(Manifest.CLASS_PATH, ' '.join(jar_classpath))
    manifest.addentry(Manifest.CREATED_BY, 'Pants_JAR_Minimizer')
    manifest.addentry(Manifest.MANIFEST_VERSION, '1.0')

    # The minimized classpath is only valid while the temporary jar it references exists
    with temporary_file_path() as classpath_jar_filepath:
      with open_jar(classpath_jar_filepath, 'w') as classpath_jar:
        classpath_jar.writestr(Manifest.PATH, manifest.contents())
      minimized_classpath = [classpath_jar_filepath] + non_jar_classpath
      yield minimized_classpath


class CommandLineGrabber(Executor):
  """Doesn't actually execute anything, just captures the cmd line."""

  def __init__(self, distribution=None):
    super(CommandLineGrabber, self).__init__(distribution=distribution)
    self._command = None  # Initialized when we run something.

  def _runner(self, classpath, main, jvm_options, args):
    self._command = self._create_command(classpath, main, jvm_options, args)
    class Runner(self.Runner):
      @property
      def executor(_):
        return self

      @property
      def cmd(_):
        return ' '.join(self._command)

      def run(_, stdout=None, stderr=None):
        return 0
    return Runner()

  @property
  def cmd(self):
    return self._command


class SubprocessExecutor(Executor):
  """Executes java programs by launching a jvm in a subprocess."""

  def __init__(self, distribution=None, scrub_classpath=True):
    super(SubprocessExecutor, self).__init__(distribution=distribution)
    self._scrub_classpath = scrub_classpath

  def _runner(self, classpath, main, jvm_options, args):
    command = self._create_command(classpath, main, jvm_options, args)

    class Runner(self.Runner):
      @property
      def executor(_):
        return self

      @property
      def cmd(_):
        return ' '.join(command)

      def run(_, stdout=None, stderr=None):
        return self._spawn(command, stdout=stdout, stderr=stderr).wait()

    return Runner()

  def spawn(self, classpath, main, jvm_options=None, args=None, **subprocess_args):
    """Spawns the java program passing any extra subprocess kwargs on to subprocess.Popen.

    Returns the Popen process object handle to the spawned java program subprocess.
    """
    cmd = self._create_command(*self._scrub_args(classpath, main, jvm_options, args))
    return self._spawn(cmd, **subprocess_args)

  def _spawn(self, cmd, **subprocess_args):
    with self._maybe_scrubbed_classpath():
      log.debug('Executing: %s' % ' '.join(cmd))
      try:
        return subprocess.Popen(cmd, **subprocess_args)
      except OSError as e:
        raise self.Error('Problem executing %s: %s' % (self._distribution.java, e))

  @contextmanager
  def _maybe_scrubbed_classpath(self):
    if self._scrub_classpath:
      classpath = os.getenv('CLASSPATH')
      if classpath:
        log.warn('Scrubbing CLASSPATH=%s' % classpath)
      with environment_as(CLASSPATH=None):
        yield
    else:
      yield