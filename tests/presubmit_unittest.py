#!/usr/bin/python
# Copyright (c) 2006-2009 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for presubmit_support.py and presubmit_canned_checks.py."""

import exceptions
import random
import string
import StringIO
import unittest

# Local imports
import __init__
import presubmit_support as presubmit
import presubmit_canned_checks
mox = __init__.mox

def String(max_length):
  return ''.join([random.choice(string.letters)
                  for x in xrange(random.randint(1, max_length))])

def Strings(max_arg_count, max_arg_length):
  return [String(max_arg_length) for x in xrange(max_arg_count)]

def Args(max_arg_count=8, max_arg_length=16):
  return Strings(max_arg_count, random.randint(1, max_arg_length))

def _DirElts(max_elt_count=4, max_elt_length=8):
  return presubmit.os.sep.join(Strings(max_elt_count, max_elt_length))

def Dir(max_elt_count=4, max_elt_length=8):
  return (random.choice((presubmit_support.os.sep, '')) +
              _DirElts(max_elt_count, max_elt_length))

def Url(max_elt_count=4, max_elt_length=8):
  return ('svn://random_host:port/a' +
          _DirElts(max_elt_count, max_elt_length).replace(os.sep, '/'))

def RootDir(max_elt_count=4, max_elt_length=8):
  return presubmit.os.sep + _DirElts(max_elt_count, max_elt_length)


class PresubmitTestsBase(mox.MoxTestBase):
  """Setups and tear downs the mocks but doesn't test anything as-is."""
  presubmit_text = """
def CheckChangeOnUpload(input_api, output_api):
  if not input_api.change.NOSUCHKEY:
    return [output_api.PresubmitError("!!")]
  elif not input_api.change.REALLYNOSUCHKEY:
    return [output_api.PresubmitPromptWarning("??")]
  elif not input_api.change.REALLYABSOLUTELYNOSUCHKEY:
    return [output_api.PresubmitPromptWarning("??"),
            output_api.PresubmitError("XX!!XX")]
  else:
    return ()
"""

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.mox.StubOutWithMock(presubmit, 'warnings')
    # Stub out 'os' but keep os.path.dirname/join/normpath and os.sep.
    os_sep = presubmit.os.sep
    os_path_join = presubmit.os.path.join
    os_path_dirname = presubmit.os.path.dirname
    os_path_normpath = presubmit.os.path.normpath
    self.mox.StubOutWithMock(presubmit, 'os')
    self.mox.StubOutWithMock(presubmit.os, 'path')
    presubmit.os.sep = os_sep
    presubmit.os.path.join = os_path_join
    presubmit.os.path.dirname = os_path_dirname
    presubmit.os.path.normpath = os_path_normpath
    self.mox.StubOutWithMock(presubmit, 'sys')
    # Special mocks.
    def MockAbsPath(f):
      return f
    presubmit.os.path.abspath = MockAbsPath
    self.mox.StubOutWithMock(presubmit.gcl, 'GetRepositoryRoot')
    fake_root_dir = RootDir()
    self.fake_root_dir = fake_root_dir
    def MockGetRepositoryRoot():
      return fake_root_dir
    presubmit.gcl.GetRepositoryRoot = MockGetRepositoryRoot
    self.mox.StubOutWithMock(presubmit.gclient, 'CaptureSVNInfo')
    self.mox.StubOutWithMock(presubmit.gcl, 'GetSVNFileProperty')
    self.mox.StubOutWithMock(presubmit.gcl, 'ReadFile')

  @staticmethod
  def MakeBasicChange(name, description):
    ci = presubmit.gcl.ChangeInfo(name=name, description=description)
    change = presubmit.GclChange(ci)
    return change

  def compareMembers(self, object, members):
    """If you add a member, be sure to add the relevant test!"""
    # Skip over members starting with '_' since they are usually not meant to
    # be for public use.
    actual_members = [x for x in sorted(dir(object))
                      if not x.startswith('_')]
    self.assertEqual(actual_members, sorted(members))


class PresubmitUnittest(PresubmitTestsBase):
  """General presubmit_support.py tests (excluding InputApi and OutputApi)."""
  def testMembersChanged(self):
    self.mox.ReplayAll()
    members = [
      'AffectedFile', 'DoPresubmitChecks', 'GclChange', 'InputApi',
      'ListRelevantPresubmitFiles', 'Main', 'NotImplementedException',
      'OutputApi', 'ParseFiles', 'PresubmitExecuter',
      'ScanSubDirs', 'SvnAffectedFile',
      'cPickle', 'cStringIO', 'deprecated', 'exceptions',
      'fnmatch', 'gcl', 'gclient', 'glob', 'marshal', 'normpath', 'optparse',
      'os', 'pickle', 'presubmit_canned_checks', 're', 'subprocess', 'sys',
      'tempfile', 'types', 'urllib2', 'warnings',
    ]
    # If this test fails, you should add the relevant test.
    self.compareMembers(presubmit, members)

  def testListRelevantPresubmitFiles(self):
    join = presubmit.os.path.join
    files = [
      'blat.cc',
      join('foo', 'haspresubmit', 'yodle', 'smart.h'),
      join('moo', 'mat', 'gat', 'yo.h'),
      join('foo', 'luck.h'),
    ]
    presubmit.os.path.isfile(join(self.fake_root_dir,
                                  'PRESUBMIT.py')).AndReturn(True)
    presubmit.os.path.isfile(join(self.fake_root_dir, 'foo',
                                  'PRESUBMIT.py')).AndReturn(False)
    presubmit.os.path.isfile(join(self.fake_root_dir, 'foo', 'haspresubmit',
                                  'PRESUBMIT.py')).AndReturn(True)
    presubmit.os.path.isfile(join(self.fake_root_dir, 'foo', 'haspresubmit',
                                  'yodle', 'PRESUBMIT.py')).AndReturn(True)
    presubmit.os.path.isfile(join(self.fake_root_dir, 'moo',
                                  'PRESUBMIT.py')).AndReturn(False)
    presubmit.os.path.isfile(join(self.fake_root_dir, 'moo', 'mat',
                                  'PRESUBMIT.py')).AndReturn(False)
    presubmit.os.path.isfile(join(self.fake_root_dir, 'moo', 'mat', 'gat',
                                  'PRESUBMIT.py')).AndReturn(False)
    #isfile(join('moo', 'PRESUBMIT.py')).AndReturn(False)
    self.mox.ReplayAll()

    presubmit_files = presubmit.ListRelevantPresubmitFiles(files,
                                                           self.fake_root_dir)
    self.assertEqual(presubmit_files,
        [
          join(self.fake_root_dir, 'PRESUBMIT.py'),
          join(self.fake_root_dir, 'foo', 'haspresubmit', 'PRESUBMIT.py'),
          join(self.fake_root_dir, 'foo', 'haspresubmit', 'yodle',
               'PRESUBMIT.py')
        ])

  def testTagLineRe(self):
    self.mox.ReplayAll()
    m = presubmit.GclChange._tag_line_re.match(' BUG =1223, 1445  \t')
    self.failUnless(m)
    self.failUnlessEqual(m.group('key'), 'BUG')
    self.failUnlessEqual(m.group('value'), '1223, 1445')

  def testGclChange(self):
    description_lines = ('Hello there',
                         'this is a change',
                         'BUG=123',
                         ' STORY =http://foo/  \t',
                         'and some more regular text  \t')
    files = [
      ['A', 'foo/blat.cc'],
      ['M', 'binary.dll'],  # a binary file
      ['A', 'isdir'],  # a directory
      ['?', 'flop/notfound.txt'],  # not found in SVN, still exists locally
      ['D', 'boo/flap.h'],
    ]
    blat = presubmit.os.path.join('foo', 'blat.cc')
    notfound = presubmit.os.path.join('flop', 'notfound.txt')
    flap = presubmit.os.path.join('boo', 'flap.h')
    presubmit.os.path.exists(blat).AndReturn(True)
    presubmit.os.path.isdir(blat).AndReturn(False)
    presubmit.os.path.exists('binary.dll').AndReturn(True)
    presubmit.os.path.isdir('binary.dll').AndReturn(False)
    presubmit.os.path.exists('isdir').AndReturn(True)
    presubmit.os.path.isdir('isdir').AndReturn(True)
    presubmit.os.path.exists(notfound).AndReturn(True)
    presubmit.os.path.isdir(notfound).AndReturn(False)
    presubmit.os.path.exists(flap).AndReturn(False)
    presubmit.gclient.CaptureSVNInfo(flap
        ).AndReturn({'Node Kind': 'file'})
    presubmit.gcl.GetSVNFileProperty(blat, 'svn:mime-type').AndReturn(None)
    presubmit.gcl.GetSVNFileProperty(
        'binary.dll', 'svn:mime-type').AndReturn('application/octet-stream')
    presubmit.gcl.GetSVNFileProperty(
        notfound, 'svn:mime-type').AndReturn('')
    presubmit.gclient.CaptureSVNInfo(blat).AndReturn(
            {'URL': 'svn:/foo/foo/blat.cc'})
    presubmit.gclient.CaptureSVNInfo('binary.dll').AndReturn(
        {'URL': 'svn:/foo/binary.dll'})
    presubmit.gclient.CaptureSVNInfo(notfound).AndReturn({})
    presubmit.gclient.CaptureSVNInfo(flap).AndReturn(
            {'URL': 'svn:/foo/boo/flap.h'})
    presubmit.gcl.ReadFile(blat).AndReturn('boo!\nahh?')
    presubmit.gcl.ReadFile(notfound).AndReturn('look!\nthere?')
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)
    change = presubmit.GclChange(ci)

    self.failUnless(change.Change() == 'mychange')
    self.failUnless(change.DescriptionText() ==
                    'Hello there\nthis is a change\nand some more regular text')
    self.failUnless(change.FullDescriptionText() ==
                    '\n'.join(description_lines))

    self.failUnless(change.BUG == '123')
    self.failUnless(change.STORY == 'http://foo/')

    self.failUnless(len(change.AffectedFiles()) == 4)
    self.failUnless(len(change.AffectedFiles(include_dirs=True)) == 5)
    self.failUnless(len(change.AffectedFiles(include_deletes=False)) == 3)
    self.failUnless(len(change.AffectedFiles(include_dirs=True,
                                             include_deletes=False)) == 4)

    affected_text_files = change.AffectedTextFiles()
    self.failUnless(len(affected_text_files) == 2)
    self.failIf(filter(lambda x: x.LocalPath() == 'binary.dll',
                       affected_text_files))

    local_paths = change.LocalPaths()
    expected_paths = [presubmit.normpath(f[1]) for f in files]
    self.failUnless(
        len(filter(lambda x: x in expected_paths, local_paths)) == 4)

    server_paths = change.ServerPaths()
    expected_paths = ['svn:/foo/%s' % f[1] for f in files if
                      f[1] != 'flop/notfound.txt']
    expected_paths.append('')  # one unknown file
    self.assertEqual(
      len(filter(lambda x: x in expected_paths, server_paths)), 4)

    files = [[x[0], presubmit.normpath(x[1])] for x in files]

    rhs_lines = []
    for line in change.RightHandSideLines():
      rhs_lines.append(line)
    self.assertEquals(rhs_lines[0][0].LocalPath(), files[0][1])
    self.assertEquals(rhs_lines[0][1], 1)
    self.assertEquals(rhs_lines[0][2],'boo!')

    self.assertEquals(rhs_lines[1][0].LocalPath(), files[0][1])
    self.assertEquals(rhs_lines[1][1], 2)
    self.assertEquals(rhs_lines[1][2], 'ahh?')

    self.assertEquals(rhs_lines[2][0].LocalPath(), files[3][1])
    self.assertEquals(rhs_lines[2][1], 1)
    self.assertEquals(rhs_lines[2][2], 'look!')

    self.assertEquals(rhs_lines[3][0].LocalPath(), files[3][1])
    self.assertEquals(rhs_lines[3][1], 2)
    self.assertEquals(rhs_lines[3][2], 'there?')

  def testExecPresubmitScript(self):
    description_lines = ('Hello there',
                         'this is a change',
                         'STORY=http://tracker/123')
    files = [
      ['A', 'foo\\blat.cc'],
    ]
    fake_presubmit = presubmit.os.path.join(self.fake_root_dir, 'PRESUBMIT.py')
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)

    executer = presubmit.PresubmitExecuter(ci, False)
    self.failIf(executer.ExecPresubmitScript('', fake_presubmit))
    # No error if no on-upload entry point
    self.failIf(executer.ExecPresubmitScript(
      ('def CheckChangeOnCommit(input_api, output_api):\n'
       '  return (output_api.PresubmitError("!!"))\n'),
      fake_presubmit
    ))

    executer = presubmit.PresubmitExecuter(ci, True)
    # No error if no on-commit entry point
    self.failIf(executer.ExecPresubmitScript(
      ('def CheckChangeOnUpload(input_api, output_api):\n'
       '  return (output_api.PresubmitError("!!"))\n'),
      fake_presubmit
    ))

    self.failIf(executer.ExecPresubmitScript(
      ('def CheckChangeOnUpload(input_api, output_api):\n'
       '  if not input_api.change.STORY:\n'
       '    return (output_api.PresubmitError("!!"))\n'
       '  else:\n'
       '    return ()'),
      fake_presubmit
    ))

    self.failUnless(executer.ExecPresubmitScript(
      ('def CheckChangeOnCommit(input_api, output_api):\n'
       '  if not input_api.change.NOSUCHKEY:\n'
       '    return [output_api.PresubmitError("!!")]\n'
       '  else:\n'
       '    return ()'),
      fake_presubmit
    ))

    self.assertRaises(exceptions.RuntimeError,
      executer.ExecPresubmitScript,
      'def CheckChangeOnCommit(input_api, output_api):\n'
      '  return "foo"',
      fake_presubmit)

    self.assertRaises(exceptions.RuntimeError,
      executer.ExecPresubmitScript,
      'def CheckChangeOnCommit(input_api, output_api):\n'
      '  return ["foo"]',
      fake_presubmit)

  def testDoPresubmitChecks(self):
    join = presubmit.os.path.join
    description_lines = ('Hello there',
                         'this is a change',
                         'STORY=http://tracker/123')
    files = [
      ['A', join('haspresubmit', 'blat.cc')],
    ]
    haspresubmit_path = join(self.fake_root_dir, 'haspresubmit', 'PRESUBMIT.py')
    root_path = join(self.fake_root_dir, 'PRESUBMIT.py')
    presubmit.os.path.isfile(root_path).AndReturn(True)
    presubmit.os.path.isfile(haspresubmit_path).AndReturn(True)
    presubmit.gcl.ReadFile(root_path,
                           'rU').AndReturn(self.presubmit_text)
    presubmit.gcl.ReadFile(haspresubmit_path,
                           'rU').AndReturn(self.presubmit_text)
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)

    output = StringIO.StringIO()
    input = StringIO.StringIO('y\n')

    self.failIf(presubmit.DoPresubmitChecks(ci, False, True, output, input,
                                            None))
    self.assertEqual(output.getvalue().count('!!'), 2)

  def testDoPresubmitChecksPromptsAfterWarnings(self):
    join = presubmit.os.path.join
    description_lines = ('Hello there',
                         'this is a change',
                         'NOSUCHKEY=http://tracker/123')
    files = [
      ['A', join('haspresubmit', 'blat.cc')],
    ]
    presubmit_path = join(self.fake_root_dir, 'PRESUBMIT.py')
    haspresubmit_path = join(self.fake_root_dir, 'haspresubmit', 'PRESUBMIT.py')
    for i in range(2):
      presubmit.os.path.isfile(presubmit_path).AndReturn(True)
      presubmit.os.path.isfile(haspresubmit_path).AndReturn(True)
      presubmit.gcl.ReadFile(presubmit_path, 'rU'
          ).AndReturn(self.presubmit_text)
      presubmit.gcl.ReadFile(haspresubmit_path, 'rU'
          ).AndReturn(self.presubmit_text)
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)

    output = StringIO.StringIO()
    input = StringIO.StringIO('n\n')  # say no to the warning
    self.failIf(presubmit.DoPresubmitChecks(ci, False, True, output, input,
                                            None))
    self.assertEqual(output.getvalue().count('??'), 2)

    output = StringIO.StringIO()
    input = StringIO.StringIO('y\n')  # say yes to the warning
    self.failUnless(presubmit.DoPresubmitChecks(ci,
                                                False,
                                                True,
                                                output,
                                                input,
                                                None))
    self.assertEquals(output.getvalue().count('??'), 2)

  def testDoPresubmitChecksNoWarningPromptIfErrors(self):
    join = presubmit.os.path.join
    description_lines = ('Hello there',
                         'this is a change',
                         'NOSUCHKEY=http://tracker/123',
                         'REALLYNOSUCHKEY=http://tracker/123')
    files = [
      ['A', join('haspresubmit', 'blat.cc')],
    ]
    presubmit_path = join(self.fake_root_dir, 'PRESUBMIT.py')
    haspresubmit_path = join(self.fake_root_dir, 'haspresubmit',
                             'PRESUBMIT.py')
    presubmit.os.path.isfile(presubmit_path).AndReturn(True)
    presubmit.os.path.isfile(haspresubmit_path).AndReturn(True)
    presubmit.gcl.ReadFile(presubmit_path, 'rU').AndReturn(self.presubmit_text)
    presubmit.gcl.ReadFile(haspresubmit_path, 'rU'
        ).AndReturn(self.presubmit_text)
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)
    output = StringIO.StringIO()
    input = StringIO.StringIO()  # should be unused
    self.failIf(presubmit.DoPresubmitChecks(ci, False, True, output, input,
                                            None))
    self.assertEqual(output.getvalue().count('??'), 2)
    self.assertEqual(output.getvalue().count('XX!!XX'), 2)
    self.assertEqual(output.getvalue().count('(y/N)'), 0)

  def testDoDefaultPresubmitChecks(self):
    join = presubmit.os.path.join
    description_lines = ('Hello there',
                         'this is a change',
                         'STORY=http://tracker/123')
    files = [
      ['A', join('haspresubmit', 'blat.cc')],
    ]
    DEFAULT_SCRIPT = """
def CheckChangeOnUpload(input_api, output_api):
  return [output_api.PresubmitError("!!")]
def CheckChangeOnCommit(input_api, output_api):
  raise Exception("Test error")
"""
    presubmit.os.path.isfile(join(self.fake_root_dir, 'PRESUBMIT.py')
        ).AndReturn(False)
    presubmit.os.path.isfile(join(self.fake_root_dir,
                                  'haspresubmit',
                                  'PRESUBMIT.py')).AndReturn(False)
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)

    
    output = StringIO.StringIO()
    input = StringIO.StringIO('y\n')
    # Always fail.
    self.failIf(presubmit.DoPresubmitChecks(ci, False, True, output, input,
                                            DEFAULT_SCRIPT))
    self.assertEquals(output.getvalue().count('!!'), 1)

  def testDirectoryHandling(self):
    files = [
      ['A', 'isdir'],
      ['A', 'isdir\\blat.cc'],
    ]
    presubmit.os.path.exists('isdir').AndReturn(True)
    presubmit.os.path.isdir('isdir').AndReturn(True)
    presubmit.os.path.exists(presubmit.os.path.join('isdir', 'blat.cc')
        ).AndReturn(True)
    presubmit.os.path.isdir(presubmit.os.path.join('isdir', 'blat.cc')
        ).AndReturn(False)
    self.mox.ReplayAll()
    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='foo',
                                  files=files)
    change = presubmit.GclChange(ci)

    affected_files = change.AffectedFiles(include_dirs=False)
    self.failUnless(len(affected_files) == 1)
    self.failUnless(affected_files[0].LocalPath().endswith('blat.cc'))
    affected_files_and_dirs = change.AffectedFiles(include_dirs=True)
    self.failUnless(len(affected_files_and_dirs) == 2)

  def testTags(self):
    DEFAULT_SCRIPT = """
def CheckChangeOnUpload(input_api, output_api):
 if input_api.change.tags['BUG'] != 'boo':
   return [output_api.PresubmitError('Tag parsing failed. 1')]
 if input_api.change.tags['STORY'] != 'http://tracker.com/42':
   return [output_api.PresubmitError('Tag parsing failed. 2')]
 if 'TEST' in input_api.change.tags:
   return [output_api.PresubmitError('Tag parsing failed. 3')]
 if input_api.change.DescriptionText() != 'Blah Blah':
   return [output_api.PresubmitError('Tag parsing failed. 4 ' + 
                                     input_api.change.DescriptionText())]
 if (input_api.change.FullDescriptionText() !=
     'Blah Blah\\n\\nSTORY=http://tracker.com/42\\nBUG=boo\\n'):
   return [output_api.PresubmitError('Tag parsing failed. 5 ' +
                                     input_api.change.FullDescriptionText())]
 return [output_api.PresubmitNotifyResult(input_api.change.tags['STORY'])]
def CheckChangeOnCommit(input_api, output_api):
  raise Exception("Test error")
"""
    self.mox.ReplayAll()

    change = presubmit.gcl.ChangeInfo(
        name='foo',
        description="Blah Blah\n\nSTORY=http://tracker.com/42\nBUG=boo\n")
    output = StringIO.StringIO()
    input = StringIO.StringIO('y\n')
    self.failUnless(presubmit.DoPresubmitChecks(change, False, True, output,
                                                input, DEFAULT_SCRIPT))
    self.assertEquals(output.getvalue(),
                      ('Warning, no presubmit.py found.\n'
                       'Running default presubmit script.\n\n'
                       '** Presubmit Messages **\n\n'
                       'http://tracker.com/42\n\n'))


class InputApiUnittest(PresubmitTestsBase):
  """Tests presubmit.InputApi."""
  def testMembersChanged(self):
    self.mox.ReplayAll()
    members = [
      'AbsoluteLocalPaths', 'AffectedFiles', 'AffectedTextFiles',
      'DepotToLocalPath', 'LocalPaths', 'LocalToDepotPath',
      'PresubmitLocalPath', 'RightHandSideLines', 'ServerPaths',
      'basename', 'cPickle', 'cStringIO', 'canned_checks', 'change',
      'marshal', 'os_path', 'pickle', 'platform',
      're', 'subprocess', 'tempfile', 'urllib2', 'version',
    ]
    # If this test fails, you should add the relevant test.
    self.compareMembers(presubmit.InputApi(None, './.'), members)

  def testDepotToLocalPath(self):
    presubmit.gclient.CaptureSVNInfo('svn://foo/smurf').AndReturn(
        {'Path': 'prout'})
    presubmit.gclient.CaptureSVNInfo('svn:/foo/notfound/burp').AndReturn({})
    self.mox.ReplayAll()

    path = presubmit.InputApi(None, './p').DepotToLocalPath('svn://foo/smurf')
    self.failUnless(path == 'prout')
    path = presubmit.InputApi(None, './p').DepotToLocalPath(
        'svn:/foo/notfound/burp')
    self.failUnless(path == None)

  def testLocalToDepotPath(self):
    presubmit.gclient.CaptureSVNInfo('smurf').AndReturn({'URL': 'svn://foo'})
    presubmit.gclient.CaptureSVNInfo('notfound-food').AndReturn({})
    self.mox.ReplayAll()

    path = presubmit.InputApi(None, './p').LocalToDepotPath('smurf')
    self.assertEqual(path, 'svn://foo')
    path = presubmit.InputApi(None, './p').LocalToDepotPath('notfound-food')
    self.failUnless(path == None)

  def testInputApiConstruction(self):
    self.mox.ReplayAll()
    # Fudge the change object, it's not used during construction anyway
    api = presubmit.InputApi(change=42, presubmit_path='foo/path/PRESUBMIT.py')
    self.assertEquals(api.PresubmitLocalPath(), 'foo/path')
    self.assertEquals(api.change, 42)

  def testInputApiPresubmitScriptFiltering(self):
    join = presubmit.os.path.join
    description_lines = ('Hello there',
                         'this is a change',
                         'BUG=123',
                         ' STORY =http://foo/  \t',
                         'and some more regular text')
    files = [
      ['A', join('foo', 'blat.cc')],
      ['M', join('foo', 'blat', 'binary.dll')],
      ['D', 'foo/mat/beingdeleted.txt'],
      ['M', 'flop/notfound.txt'],
      ['A', 'boo/flap.h'],
    ]

  
    blat = join('foo', 'blat.cc')
    binary = join('foo', 'blat', 'binary.dll')
    beingdeleted = join('foo', 'mat', 'beingdeleted.txt')
    notfound = join('flop', 'notfound.txt')
    flap = join('boo', 'flap.h')
    presubmit.os.path.exists(blat).AndReturn(True)
    presubmit.os.path.isdir(blat).AndReturn(False)
    presubmit.os.path.exists(binary).AndReturn(True)
    presubmit.os.path.isdir(binary).AndReturn(False)
    presubmit.os.path.exists(beingdeleted).AndReturn(False)
    presubmit.os.path.exists(notfound).AndReturn(False)
    presubmit.os.path.exists(flap).AndReturn(True)
    presubmit.os.path.isdir(flap).AndReturn(False)
    presubmit.gclient.CaptureSVNInfo(beingdeleted).AndReturn({})
    presubmit.gclient.CaptureSVNInfo(notfound).AndReturn({})
    presubmit.gcl.GetSVNFileProperty(blat, 'svn:mime-type').AndReturn(None)
    presubmit.gcl.GetSVNFileProperty(binary, 'svn:mime-type').AndReturn(
        'application/octet-stream')
    presubmit.gcl.ReadFile(blat).AndReturn('whatever\ncookie')
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange',
                                  description='\n'.join(description_lines),
                                  files=files)
    change = presubmit.GclChange(ci)
    api = presubmit.InputApi(change, 'foo/PRESUBMIT.py')
    affected_files = api.AffectedFiles()
    self.assertEquals(len(affected_files), 3)
    self.assertEquals(affected_files[0].LocalPath(),
                      presubmit.normpath('foo/blat.cc'))
    self.assertEquals(affected_files[1].LocalPath(),
                      presubmit.normpath('foo/blat/binary.dll'))
    self.assertEquals(affected_files[2].LocalPath(),
                      presubmit.normpath('foo/mat/beingdeleted.txt'))
    rhs_lines = []
    for line in api.RightHandSideLines():
      rhs_lines.append(line)
    self.assertEquals(len(rhs_lines), 2)
    self.assertEqual(rhs_lines[0][0].LocalPath(),
                    presubmit.normpath('foo/blat.cc'))

  def testGetAbsoluteLocalPath(self):
    join = presubmit.os.path.join
    normpath = presubmit.normpath
    # Regression test for bug of presubmit stuff that relies on invoking
    # SVN (e.g. to get mime type of file) not working unless gcl invoked
    # from the client root (e.g. if you were at 'src' and did 'cd base' before
    # invoking 'gcl upload' it would fail because svn wouldn't find the files
    # the presubmit script was asking about).
    files = [
      ['A', 'isdir'],
      ['A', join('isdir', 'blat.cc')],
      ['M', join('elsewhere', 'ouf.cc')],
    ]
    self.mox.ReplayAll()

    ci = presubmit.gcl.ChangeInfo(name='mychange', description='', files=files)
    # It doesn't make sense on non-Windows platform. This is somewhat hacky,
    # but it is needed since we can't just use os.path.join('c:', 'temp').
    change = presubmit.GclChange(ci, self.fake_root_dir)
    affected_files = change.AffectedFiles(include_dirs=True)
    # Local paths should remain the same
    self.assertEquals(affected_files[0].LocalPath(), normpath('isdir'))
    self.assertEquals(affected_files[1].LocalPath(), normpath('isdir/blat.cc'))
    # Absolute paths should be prefixed
    self.assertEquals(affected_files[0].AbsoluteLocalPath(),
                      normpath(join(self.fake_root_dir, 'isdir')))
    self.assertEquals(affected_files[1].AbsoluteLocalPath(),
                      normpath(join(self.fake_root_dir, 'isdir/blat.cc')))

    # New helper functions need to work
    paths_from_change = change.AbsoluteLocalPaths(include_dirs=True)
    self.assertEqual(len(paths_from_change), 3)
    presubmit_path = join(self.fake_root_dir, 'isdir', 'PRESUBMIT.py')
    api = presubmit.InputApi(change=change, presubmit_path=presubmit_path)
    paths_from_api = api.AbsoluteLocalPaths(include_dirs=True)
    self.assertEqual(len(paths_from_api), 2)
    for absolute_paths in [paths_from_change, paths_from_api]:
      self.assertEqual(absolute_paths[0],
                       normpath(join(self.fake_root_dir, 'isdir')))
      self.assertEqual(absolute_paths[1],
                       normpath(join(self.fake_root_dir, 'isdir', 'blat.cc')))

  def testDeprecated(self):
    presubmit.warnings.warn(mox.IgnoreArg(), category=mox.IgnoreArg(),
                            stacklevel=2)
    self.mox.ReplayAll()
    change = presubmit.GclChange(
        presubmit.gcl.ChangeInfo(name='mychange', description='Bleh\n'))
    api = presubmit.InputApi(change, 'foo/PRESUBMIT.py')
    api.AffectedTextFiles(include_deletes=False)


class OuputApiUnittest(PresubmitTestsBase):
  """Tests presubmit.OutputApi."""
  def testMembersChanged(self):
    self.mox.ReplayAll()
    members = [
      'MailTextResult', 'PresubmitError', 'PresubmitNotifyResult',
      'PresubmitPromptWarning', 'PresubmitResult',
    ]
    # If this test fails, you should add the relevant test.
    self.compareMembers(presubmit.OutputApi(), members)

  def testOutputApiBasics(self):
    self.mox.ReplayAll()
    self.failUnless(presubmit.OutputApi.PresubmitError('').IsFatal())
    self.failIf(presubmit.OutputApi.PresubmitError('').ShouldPrompt())

    self.failIf(presubmit.OutputApi.PresubmitPromptWarning('').IsFatal())
    self.failUnless(
        presubmit.OutputApi.PresubmitPromptWarning('').ShouldPrompt())

    self.failIf(presubmit.OutputApi.PresubmitNotifyResult('').IsFatal())
    self.failIf(presubmit.OutputApi.PresubmitNotifyResult('').ShouldPrompt())

    # TODO(joi) Test MailTextResult once implemented.

  def testOutputApiHandling(self):
    self.mox.ReplayAll()
    output = StringIO.StringIO()
    unused_input = StringIO.StringIO()
    error = presubmit.OutputApi.PresubmitError('!!!')
    self.failIf(error._Handle(output, unused_input))
    self.failUnless(output.getvalue().count('!!!'))

    output = StringIO.StringIO()
    notify = presubmit.OutputApi.PresubmitNotifyResult('?see?')
    self.failUnless(notify._Handle(output, unused_input))
    self.failUnless(output.getvalue().count('?see?'))

    output = StringIO.StringIO()
    input = StringIO.StringIO('y')
    warning = presubmit.OutputApi.PresubmitPromptWarning('???')
    self.failUnless(warning._Handle(output, input))
    self.failUnless(output.getvalue().count('???'))

    output = StringIO.StringIO()
    input = StringIO.StringIO('n')
    warning = presubmit.OutputApi.PresubmitPromptWarning('???')
    self.failIf(warning._Handle(output, input))
    self.failUnless(output.getvalue().count('???'))

    output = StringIO.StringIO()
    input = StringIO.StringIO('\n')
    warning = presubmit.OutputApi.PresubmitPromptWarning('???')
    self.failIf(warning._Handle(output, input))
    self.failUnless(output.getvalue().count('???'))


class AffectedFileUnittest(PresubmitTestsBase):
  def testMembersChanged(self):
    self.mox.ReplayAll()
    members = [
      'AbsoluteLocalPath', 'Action', 'IsDirectory', 'IsTextFile', 'LocalPath',
      'NewContents', 'OldContents', 'OldFileTempPath', 'Property', 'ServerPath',
    ]
    # If this test fails, you should add the relevant test.
    self.compareMembers(presubmit.AffectedFile('a', 'b'), members)
    self.compareMembers(presubmit.SvnAffectedFile('a', 'b'), members)

  def testAffectedFile(self):
    path = presubmit.os.path.join('foo', 'blat.cc')
    presubmit.os.path.exists(path).AndReturn(True)
    presubmit.os.path.isdir(path).AndReturn(False)
    presubmit.gcl.ReadFile(path).AndReturn('whatever\ncookie')
    presubmit.gclient.CaptureSVNInfo(path).AndReturn(
        {'URL': 'svn:/foo/foo/blat.cc'})
    self.mox.ReplayAll()
    af = presubmit.SvnAffectedFile('foo/blat.cc', 'M')
    self.failUnless(af.ServerPath() == 'svn:/foo/foo/blat.cc')
    self.failUnless(af.LocalPath() == presubmit.normpath('foo/blat.cc'))
    self.failUnless(af.Action() == 'M')
    self.assertEquals(af.NewContents(), ['whatever', 'cookie'])
    af = presubmit.AffectedFile('notfound.cc', 'A')
    self.failUnless(af.ServerPath() == '')

  def testProperty(self):
    presubmit.gcl.GetSVNFileProperty('foo.cc', 'svn:secret-property'
        ).AndReturn('secret-property-value')
    self.mox.ReplayAll()
    affected_file = presubmit.SvnAffectedFile('foo.cc', 'A')
    # Verify cache coherency.
    self.failUnless(affected_file.Property('svn:secret-property') ==
                    'secret-property-value')
    self.failUnless(affected_file.Property('svn:secret-property') ==
                    'secret-property-value')

  def testIsDirectoryNotExists(self):
    presubmit.os.path.exists('foo.cc').AndReturn(False)
    presubmit.gclient.CaptureSVNInfo('foo.cc').AndReturn({})
    self.mox.ReplayAll()
    affected_file = presubmit.SvnAffectedFile('foo.cc', 'A')
    # Verify cache coherency.
    self.failIf(affected_file.IsDirectory())
    self.failIf(affected_file.IsDirectory())

  def testIsDirectory(self):
    presubmit.os.path.exists('foo.cc').AndReturn(True)
    presubmit.os.path.isdir('foo.cc').AndReturn(True)
    self.mox.ReplayAll()
    affected_file = presubmit.SvnAffectedFile('foo.cc', 'A')
    # Verify cache coherency.
    self.failUnless(affected_file.IsDirectory())
    self.failUnless(affected_file.IsDirectory())

  def testIsTextFile(self):
    list = [presubmit.SvnAffectedFile('foo/blat.txt', 'M'),
            presubmit.SvnAffectedFile('foo/binary.blob', 'M'),
            presubmit.SvnAffectedFile('blat/flop.txt', 'D')]
    blat = presubmit.os.path.join('foo', 'blat.txt')
    blob = presubmit.os.path.join('foo', 'binary.blob')
    presubmit.os.path.exists(blat).AndReturn(True)
    presubmit.os.path.isdir(blat).AndReturn(False)
    presubmit.os.path.exists(blob).AndReturn(True)
    presubmit.os.path.isdir(blob).AndReturn(False)
    presubmit.gcl.GetSVNFileProperty(blat, 'svn:mime-type').AndReturn(None)
    presubmit.gcl.GetSVNFileProperty(blob, 'svn:mime-type'
        ).AndReturn('application/octet-stream')
    self.mox.ReplayAll()

    output = filter(lambda x: x.IsTextFile(), list)
    self.failUnless(len(output) == 1)
    self.failUnless(list[0] == output[0])


class CannedChecksUnittest(PresubmitTestsBase):
  """Tests presubmit_canned_checks.py."""
  class MockInputApi(object):
    class MockUrllib2(object):
      class urlopen(object):
        def __init__(self, url):
          if url == 'url_to_open':
            self.result = '1'
          else:
            self.result = '0'
        def read(self):
          return self.result
        def close(self):
          pass
    def __init__(self, lines=None):
      self.lines = lines
      self.basename = lambda x: x
      self.urllib2 = self.MockUrllib2()
      self.re = presubmit.re

    def RightHandSideLines(self):
      for line in self.lines:
        yield (presubmit.AffectedFile('bingo', 'M'), 1, line)

  def testMembersChanged(self):
    self.mox.ReplayAll()
    members = [
      'CheckChangeHasBugField', 'CheckChangeHasNoTabs',
      'CheckChangeHasQaField', 'CheckChangeHasTestedField',
      'CheckChangeHasTestField', 'CheckDoNotSubmit',
      'CheckDoNotSubmitInDescription', 'CheckDoNotSubmitInFiles',
      'CheckLongLines', 'CheckTreeIsOpen', 'RunPythonUnitTests',
    ]
    # If this test fails, you should add the relevant test.
    self.compareMembers(presubmit_canned_checks, members)

  def testCannedCheckChangeHasBugField(self):
    self.mox.ReplayAll()
    change = self.MakeBasicChange('foo',
                                  'Foo\nBUG=1234')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failIf(presubmit_canned_checks.CheckChangeHasBugField(
        api, presubmit.OutputApi))

    change = self.MakeBasicChange('foo',
                                  'Foo\nNEVERTESTED=did some stuff')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failUnless(presubmit_canned_checks.CheckChangeHasBugField(
        api, presubmit.OutputApi))

  def testCannedCheckChangeHasTestField(self):
    self.mox.ReplayAll()
    change = self.MakeBasicChange('foo',
                                  'Foo\nTEST=did some stuff')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failIf(presubmit_canned_checks.CheckChangeHasTestField(
        api, presubmit.OutputApi))

    change = self.MakeBasicChange('foo',
                                  'Foo\nNOTEST=did some stuff')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failUnless(presubmit_canned_checks.CheckChangeHasTestField(
        api, presubmit.OutputApi))

  def testCannedCheckChangeHasTestedField(self):
    self.mox.ReplayAll()
    change = self.MakeBasicChange('foo',
                                  'Foo\nTESTED=did some stuff')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failIf(presubmit_canned_checks.CheckChangeHasTestedField(
        api, presubmit.OutputApi))

    change = self.MakeBasicChange('foo',
                                  'Foo\nNEVERTESTED=did some stuff')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failUnless(presubmit_canned_checks.CheckChangeHasTestedField(
        api, presubmit.OutputApi))

  def testCannedCheckChangeHasQAField(self):
    self.mox.ReplayAll()
    change = self.MakeBasicChange('foo',
                                  'Foo\nQA=test floop feature very well')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failIf(presubmit_canned_checks.CheckChangeHasQaField(
        api, presubmit.OutputApi))

    change = self.MakeBasicChange('foo',
                                  'Foo\nNOTFORQA=test floop feature very well')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failUnless(presubmit_canned_checks.CheckChangeHasQaField(
        api, presubmit.OutputApi))

  def testCannedCheckDoNotSubmitInDescription(self):
    self.mox.ReplayAll()
    change = self.MakeBasicChange('foo', 'hello')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failIf(presubmit_canned_checks.CheckDoNotSubmitInDescription(
        api, presubmit.OutputApi))

    change = self.MakeBasicChange('foo',
                                  'DO NOT ' + 'SUBMIT')
    api = presubmit.InputApi(change, './PRESUBMIT.py')
    self.failUnless(presubmit_canned_checks.CheckDoNotSubmitInDescription(
        api, presubmit.OutputApi))

  def testCannedCheckDoNotSubmitInFiles(self):
    self.mox.ReplayAll()
    self.failIf(presubmit_canned_checks.CheckDoNotSubmitInFiles(
      self.MockInputApi(['hello', 'there']), presubmit.OutputApi
    ))
    self.failUnless(presubmit_canned_checks.CheckDoNotSubmitInFiles(
      self.MockInputApi(['hello', 'yo, DO NOT ' + 'SUBMIT']),
                      presubmit.OutputApi))

  def testCannedCheckChangeHasNoTabs(self):
    self.mox.ReplayAll()
    self.failIf(presubmit_canned_checks.CheckChangeHasNoTabs(
      self.MockInputApi(['hello', 'there']), presubmit.OutputApi
    ))
    self.failUnless(presubmit_canned_checks.CheckChangeHasNoTabs(
      self.MockInputApi(['hello', 'there\tit is']), presubmit.OutputApi
    ))

  def testCannedCheckLongLines(self):
    self.mox.ReplayAll()
    self.failIf(presubmit_canned_checks.CheckLongLines(
      self.MockInputApi(['hello', 'there']), presubmit.OutputApi, 5
    ))
    self.failUnless(presubmit_canned_checks.CheckLongLines(
      self.MockInputApi(['hello', 'there!']), presubmit.OutputApi, 5
    ))

  def testCannedCheckTreeIsOpen(self):
    self.mox.ReplayAll()
    self.failIf(presubmit_canned_checks.CheckTreeIsOpen(
      self.MockInputApi(), presubmit.OutputApi, url='url_to_open', closed='0'
    ))
    self.failUnless(presubmit_canned_checks.CheckTreeIsOpen(
      self.MockInputApi(), presubmit.OutputApi, url='url_to_closed', closed='0'
    ))

  def RunPythonUnitTests(self):
    self.mox.ReplayAll()
    # TODO(maruel): Add real tests.
    self.failIf(presubmit_canned_checks.RunPythonUnitTests(
        self.MockInputApi(),
        presubmit.OutputApi, []))
    self.failUnless(presubmit_canned_checks.RunPythonUnitTests(
        self.MockInputApi(),
        presubmit.OutputApi, ['non_existent_module']))

if __name__ == '__main__':
  unittest.main()
