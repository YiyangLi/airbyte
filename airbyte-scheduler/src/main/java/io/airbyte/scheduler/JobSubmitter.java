/*
 * MIT License
 *
 * Copyright (c) 2020 Airbyte
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package io.airbyte.scheduler;

import com.google.common.annotations.VisibleForTesting;
import com.google.common.base.Charsets;
import com.google.common.base.Strings;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMap.Builder;
import io.airbyte.analytics.TrackingClientSingleton;
import io.airbyte.commons.concurrency.LifecycledCallable;
import io.airbyte.config.StandardDestinationDefinition;
import io.airbyte.config.StandardSourceDefinition;
import io.airbyte.config.StandardSyncSchedule;
import io.airbyte.config.helpers.ScheduleHelpers;
import io.airbyte.config.persistence.ConfigNotFoundException;
import io.airbyte.config.persistence.ConfigRepository;
import io.airbyte.scheduler.persistence.JobPersistence;
import io.airbyte.validation.json.JsonValidationException;
import io.airbyte.workers.WorkerConstants;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

public class JobSubmitter implements Runnable {

  private static final Logger LOGGER = LoggerFactory.getLogger(JobSubmitter.class);

  private final JobPersistence persistence;
  private final JobTracking jobTracker;

  public JobSubmitter(final JobPersistence persistence, final JobTracking jobTracker) {
    this.persistence = persistence;
    this.jobTracker = jobTracker;
  }

  @Override
  public void run() {
    try {
      LOGGER.info("Running job-submitter...");

      final Optional<Job> nextJob = persistence.getNextJob();

      nextJob.ifPresent(job -> {
        jobTracker.trackSubmission(job);
        submitJob(job);
        LOGGER.info("Job-Submitter Summary. Submitted job with scope {}", job.getScope());
      });

      LOGGER.info("Completed Job-Submitter...");
    } catch (Throwable e) {
      LOGGER.error("Job Submitter Error", e);
    }
  }

  @VisibleForTesting
  void submitJob(Job job) {
    // temporal submit.
    // not a great story on how we recover from this submission failing...
    final UUID temporalId = temporalClient.submit(job); // maybe need to all submit info from workerrunfactory.
    // get temporal id
    persistence.writeTemporalId(job.getId(), temporalId);
    // save temporal id
  }
}
