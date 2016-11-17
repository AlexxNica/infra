# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from contextlib import contextmanager

from recipe_engine import recipe_api


class GomaApi(recipe_api.RecipeApi):
    """GomaApi contains helper functions for using goma."""

    def __init__(self, **kwargs):
        super(GomaApi, self).__init__(**kwargs)
        self._goma_dir = None
        self._goma_started = False

        self._goma_ctl_env = {}
        self._goma_jobs = None

    @property
    def service_account_json_path(self):
        return '/creds/service_accounts/service-account-goma-client.json'

    @property
    def json_path(self):
        assert self._goma_dir
        return self.m.path.join(self._goma_dir, 'jsonstatus')

    @property
    def recommended_goma_jobs(self):
        """
        Return the recommended number of jobs for parallel build using Goma.

        This function caches the _goma_jobs.
        """
        if self._goma_jobs:
            return self._goma_jobs

        # We need to use python.inline not to change behavior of recipes.
        step_result = self.m.python.inline(
            'calculate the number of recommended jobs',
            """
import multiprocessing
import sys

job_limit = 200
if sys.platform.startswith('linux'):
  # Use 80 for linux not to load goma backend.
  job_limit = 80

try:
  jobs = min(job_limit, multiprocessing.cpu_count() * 10)
except NotImplementedError:
  jobs = 50

print jobs
            """,
            stdout=self.m.raw_io.output(),
            step_test_data=(
                lambda: self.m.raw_io.test_api.stream_output('50\n'))
        )
        self._goma_jobs = int(step_result.stdout)

        return self._goma_jobs

    def ensure_goma(self, canary=False):
        with self.m.step.nest('ensure_goma'):
            with self.m.step.context({'infra_step': True}):
                try:
                    self.m.cipd.set_service_account_credentials(
                        self.service_account_json_path)

                    self.m.cipd.install_client()
                    goma_package = ('infra_internal/goma/client/%s' %
                        self.m.cipd.platform_suffix())
                    ref='release'
                    if canary:
                        ref='candidate'
                    self._goma_dir = self.m.path['cache'].join('cipd', 'goma')

                    self.m.cipd.ensure(self._goma_dir, {goma_package: ref})

                    return self._goma_dir
                except self.m.step.StepFailure: # pragma: no cover
                    return None

    @property
    def goma_ctl(self):
        return self.m.path.join(self._goma_dir, 'goma_ctl.py')

    @property
    def goma_dir(self):
        assert self._goma_dir
        return self._goma_dir

    def start(self, env=None, **kwargs):
        """Start goma compiler_proxy.

        A user MUST execute ensure_goma beforehand.
        It is user's responsibility to handle failure of starting compiler_proxy.
        """
        assert self._goma_dir
        assert not self._goma_started

        self._goma_ctl_env['GOMA_CACHE_DIR'] = (
            self.m.path.join(self.m.path['cache'], 'goma'))
        self._goma_ctl_env['GOMA_SERVICE_ACCOUNT_JSON_FILE'] = (
            self.service_account_json_path)

        # GLOG_log_dir should not be set.
        assert env is None or 'GLOG_log_dir' not in env

        goma_ctl_start_env = self._goma_ctl_env.copy()
        if env is not None:
            goma_ctl_start_env.update(env)

        try:
            self.m.python(
                name='start_goma',
                script=self.goma_ctl,
                args=['restart'], env=goma_ctl_start_env, infra_step=True, **kwargs)
            self._goma_started = True
        except self.m.step.InfraFailure as e: # pragma: no cover
            try:
                with self.m.step.defer_results():
                    self.m.python(
                        name='stop_goma (start failure)',
                        script=self.goma_ctl,
                        args=['stop'], env=self._goma_ctl_env, **kwargs)
            except self.m.step.StepFailure:
                pass
            raise e

    def stop(self, **kwargs):
        """Stop goma compiler_proxy.

        A user MUST execute start beforehand.
        It is user's responsibility to handle failure of stopping compiler_proxy.

        Raises:
            StepFailure if it fails to stop goma.
        """
        assert self._goma_dir
        assert self._goma_started

        with self.m.step.defer_results():
            self.m.python(name='goma_jsonstatus', script=self.goma_ctl,
                          args=['jsonstatus', self.json_path],
                          env=self._goma_ctl_env, **kwargs)
            self.m.python(name='goma_stat', script=self.goma_ctl,
                          args=['stat'],
                          env=self._goma_ctl_env, **kwargs)
            self.m.python(name='stop_goma', script=self.goma_ctl,
                          args=['stop'], env=self._goma_ctl_env, **kwargs)

        self._goma_started = False
        self._goma_ctl_env = {}

    @contextmanager
    def build_with_goma(self, env=None):
        """Make context wrapping goma start/stop.

        Raises:
            StepFailure or InfraFailure if it fails to build.
        """

        self.start(env)
        try:
            yield
        finally:
            self.stop()