// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package presubmit

// This file contains all the functions that contain Jenkins-specific logic.  Other
// files should be able to reference these functions without knowing what CI system
// is backing them.  No other files should even mention Jenkins.

import (
	"fmt"
	"net/url"
	"strings"

	"v.io/jiri/gerrit"
	"v.io/jiri/jenkins"
)

var (
	jenkinsHost              = "http://localhost:8090/jenkins"
	jenkinsPresubmitTestName = "mojo-presubmit-test"
	jenkinsInstance          *jenkins.Jenkins
)

// getJenkins returns a handle to the Jenkins instance in a non-thread-safe singleton fashion.
func getJenkins() (*jenkins.Jenkins, error) {
	if jenkinsInstance != nil {
		return jenkinsInstance, nil
	}
	var err error
	jenkinsInstance, err = jenkins.New(jenkinsHost)
	return jenkinsInstance, err
}

// LastPresubmitBuildError returns the error of the last presubmit build, or nil if the build
// succeeded.  It also returns an error if we fail to fetch the status of the build.
func LastPresubmitBuildError() error {
	j, err := getJenkins()
	if err != nil {
		return err
	}

	lastBuildInfo, err := j.LastCompletedBuildStatus(jenkinsPresubmitTestName, nil)
	if err != nil {
		return err
	}

	if lastBuildInfo.Result == "FAILURE" {
		return fmt.Errorf("%s build result was FAILURE", jenkinsPresubmitTestName)
	}

	return nil
}

// RemoveOutdatedBuilds halts and removes presubmit builds that are no longer relevant.  This
// could happen because a contributor uploads a new patch set before the old one is finished testing.
func RemoveOutdatedBuilds(validCLs map[CLNumber]Patchset) (errs []error) {
	fmt.Println("Removing outdated builds (if you believe this suspicious looking log message)")
	// TODO(lanechr): everything.
	return nil
}

// AddPresubmitTestBuild actually kicks off the presubmit test build on Jenkins.
func AddPresubmitTestBuild(cls gerrit.CLList, testNames []string) error {
	j, err := getJenkins()
	if err != nil {
		return err
	}

	refs := []string{}
	for _, cl := range cls {
		refs = append(refs, cl.Reference())
	}

	if err := j.AddBuildWithParameter(jenkinsPresubmitTestName, url.Values{
		"REFS":  {strings.Join(refs, " ")},
		"TESTS": {strings.Join(testNames, " ")},
	}); err != nil {
		return err
	}

	return nil
}

// GetTestsToRun returns the list of tests we should run on CLs.  In the original version of this function
// from V23, it loaded a config from their tooldata package and cross-checked it with a list of given projects,
// running only the tests that were associated with those projects.  So naturally, we just hardcode a list :P
func GetTestsToRun() []string {
	// TODO(lanechr): replace this function with something that returns just the tests
	// that are affected by the CLs we're testing.
	return []string{
		"ignore-mojo-linux-debug",
		"ignore-mojo-linux-release",
		"ignore-mojo-linux-asan-debug",
		"ignore-mojo-linux-asan-release",
	}
}
