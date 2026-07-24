document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const role = body.dataset.role;
  if (role) {
    body.classList.add(`role-context-${role}`);
  }

  initPageLoadOverlay();
  initButtonLoaders();
  initSectionHelpToggle();
  initSectionPlayer();
  initFullTestPlayer();
  initModalDialogs();
});

function initPageLoadOverlay() {
  const loader = document.querySelector("[data-page-loader]");
  if (!loader) {
    return;
  }

  const isPrimaryActivation = (event) => {
    if (event.defaultPrevented) {
      return false;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return false;
    }
    if ("button" in event && event.button !== 0) {
      return false;
    }
    return true;
  };

  const togglePlayerLoader = (isVisible) => {
    const fullscreenHost = document.fullscreenElement;
    const playerLoader = fullscreenHost?.querySelector?.("[data-player-loader]");
    if (!playerLoader) {
      return;
    }
    if (isVisible) {
      playerLoader.removeAttribute("hidden");
    } else {
      playerLoader.setAttribute("hidden", "");
    }
  };

  const showLoader = () => {
    loader.removeAttribute("hidden");
    document.body.classList.add("is-loading");
    togglePlayerLoader(true);
  };

  const hideLoader = () => {
    loader.setAttribute("hidden", "");
    document.body.classList.remove("is-loading");
    document.querySelectorAll("[data-player-loader]").forEach((playerLoader) => {
      playerLoader.setAttribute("hidden", "");
    });
  };

  window.showPageLoader = showLoader;
  window.hidePageLoader = hideLoader;
  hideLoader();
  window.addEventListener("pageshow", hideLoader);

  const navigateWithLoader = (anchor) => {
    if (!(anchor instanceof HTMLAnchorElement)) {
      return false;
    }
    if (!anchor.href || anchor.target === "_blank" || anchor.hasAttribute("download")) {
      return false;
    }
    const destination = new URL(anchor.href, window.location.href);
    if (destination.origin !== window.location.origin) {
      return false;
    }
    showLoader();
    window.requestAnimationFrame(() => {
      window.location.assign(destination.href);
    });
    return true;
  };

  document.addEventListener("pointerdown", (event) => {
    const trigger = event.target.closest("[data-page-loader-trigger]");
    if (!trigger || !isPrimaryActivation(event)) {
      return;
    }
    showLoader();
  });

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-page-loader-trigger]");
    if (!trigger || !isPrimaryActivation(event)) {
      return;
    }
    if (navigateWithLoader(trigger)) {
      event.preventDefault();
      return;
    }
    showLoader();
  });
}

function initButtonLoaders() {
  const setButtonLoading = (trigger) => {
    if (!(trigger instanceof HTMLElement)) {
      return;
    }
    const isButtonStyle = trigger.classList.contains("button") || trigger.classList.contains("button-secondary");
    if (!isButtonStyle || trigger.classList.contains("is-loading")) {
      return;
    }
    if (!trigger.querySelector(".btn-spinner")) {
      const spinner = document.createElement("span");
      spinner.className = "btn-spinner";
      spinner.setAttribute("aria-hidden", "true");
      trigger.appendChild(spinner);
    }
    trigger.classList.add("is-loading");
    if (trigger instanceof HTMLButtonElement || trigger instanceof HTMLInputElement) {
      trigger.disabled = true;
    }
  };

  const clearButtonLoading = (trigger) => {
    if (!(trigger instanceof HTMLElement)) {
      return;
    }
    trigger.classList.remove("is-loading");
    if (trigger instanceof HTMLButtonElement || trigger instanceof HTMLInputElement) {
      trigger.disabled = false;
    }
  };

  const resetButtonLoading = () => {
    document.querySelectorAll(".is-loading").forEach((el) => {
      el.classList.remove("is-loading");
      if (el instanceof HTMLButtonElement || el instanceof HTMLInputElement) {
        el.disabled = false;
      }
    });
  };

  window.setButtonLoading = setButtonLoading;
  window.clearButtonLoading = clearButtonLoading;

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest(
      "a[data-show-loader], button[data-show-loader], input[data-show-loader], a[data-btn-loader], button[data-btn-loader], input[data-btn-loader]"
    );
    if (!trigger || event.defaultPrevented) {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
      return;
    }
    if (trigger instanceof HTMLButtonElement && trigger.disabled) {
      return;
    }
    setButtonLoading(trigger);
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || event.defaultPrevented) {
      return;
    }
    if (form.dataset.showLoader === undefined && form.dataset.btnLoader === undefined) {
      return;
    }
    const submitter = event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
    setButtonLoading(submitter);
  });

  window.addEventListener("pageshow", resetButtonLoading);
}

function initModalDialogs() {
  const modals = Array.from(document.querySelectorAll("[data-modal]"));
  if (!modals.length) {
    return;
  }

  const updateBodyLock = () => {
    const hasOpenModal = modals.some((modal) => !modal.hasAttribute("hidden"));
    document.body.classList.toggle("has-open-modal", hasOpenModal);
  };

  const openModal = (modal) => {
    if (!modal) return;
    modal.removeAttribute("hidden");
    updateBodyLock();
  };

  const closeModal = (modal) => {
    if (!modal) return;
    modal.setAttribute("hidden", "");
    updateBodyLock();
  };

  document.querySelectorAll("[data-modal-open]").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      openModal(document.getElementById(trigger.dataset.modalOpen));
    });
  });

  modals.forEach((modal) => {
    modal.querySelectorAll("[data-modal-close]").forEach((closer) => {
      closer.addEventListener("click", () => closeModal(modal));
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") {
      return;
    }
    modals.forEach((modal) => {
      if (!modal.hasAttribute("hidden")) {
        closeModal(modal);
      }
    });
  });

  updateBodyLock();
}

function initSectionHelpToggle() {
  const toggle = document.querySelector("[data-section-help-toggle]");
  const panel = document.querySelector("[data-section-help-panel]");
  const chevron = toggle?.querySelector(".section-help-chevron");

  if (!toggle || !panel) {
    return;
  }

  toggle.addEventListener("click", () => {
    const isExpanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!isExpanded));
    if (isExpanded) {
      panel.setAttribute("hidden", "");
      panel.classList.remove("open");
      if (chevron) chevron.style.transform = "rotate(0deg)";
    } else {
      panel.removeAttribute("hidden");
      panel.classList.add("open");
      if (chevron) chevron.style.transform = "rotate(180deg)";
    }
  });
}

function initSectionPlayer() {
  const player = document.querySelector("[data-test-player]");
  const practiceDataScript = document.getElementById("section-practice-question-data");
  const testDataScript = document.getElementById("section-test-question-data");

  if (!player || !practiceDataScript || !testDataScript) {
    return;
  }

  const practiceQuestions = JSON.parse(practiceDataScript.textContent || "[]");
  let testQuestions = JSON.parse(testDataScript.textContent || "[]");
  let currentIndex = 0;
  let correctCount = 0;
  let feedbackTimeout = null;
  let activeMode = player.dataset.mode || "practice";
  const assessmentType = player.dataset.assessmentType || "prepgia";
  const sectionKey = player.dataset.sectionKey || "";
  const practiceTotal = Number(player.dataset.practiceTotal || 0);
  let practiceSolved = Number(player.dataset.practiceSolved || 0);
  const timeLimitSeconds = Number(player.dataset.timeLimitSeconds || 0);
  let remainingSeconds = timeLimitSeconds;
  let timerInterval = null;
  let finished = false;
  let testStarted = false;
  let practiceStarted = false;
  let practiceElapsedSeconds = 0;
  let practiceTimerInterval = null;
  const submittedAnswers = [];
  let testSetupLoaded = testQuestions.length > 0;

  const seedEl = player.querySelector("[data-test-seed]");
  const progressEl = player.querySelector("[data-test-progress]");
  const progressFillEl = player.querySelector("[data-test-progress-fill]");
  const practiceProgressWrapEl = player.querySelector("[data-practice-progress-wrap]");
  const practiceProgressCopyEl = player.querySelector("[data-practice-progress-copy]");
  const timerEl = player.querySelector("[data-test-timer]");
  const feedbackEl = player.querySelector("[data-feedback-banner]");
  const completeSummaryEl = player.querySelector("[data-complete-summary]");
  const contextEl = player.querySelector("[data-test-context]");
  const contextHelperEl = player.querySelector("[data-test-context-helper]");
  const questionEl = player.querySelector("[data-test-question]");
  const optionsEl = player.querySelector("[data-test-options]");
  const modeCopyEl = player.querySelector(".section-mode-copy");
  const modeButtons = player.querySelectorAll("[data-player-mode]");
  const railPhaseEl = player.querySelector("[data-test-rail-phase]");
  const railProgressEl = player.querySelector("[data-test-progress]");

  const contextStage = player.querySelector('[data-test-stage="context"]');
  const questionStage = player.querySelector('[data-test-stage="question"]');
  const completeStage = player.querySelector('[data-test-stage="complete"]');
  const practiceIntroStage = player.querySelector('[data-test-stage="practice-intro"]');
  const testIntroStage = player.querySelector('[data-test-stage="test-intro"]');
  const loadingStage = player.querySelector('[data-test-stage="loading"]');
  const fullscreenStartButton = player.querySelector("[data-test-fullscreen-start]");
  const practiceStartButton = player.querySelector("[data-test-practice-start]");
  const endTestButton = player.querySelector("[data-test-end]");
  const returnUrl = player.dataset.returnUrl || player.dataset.dashboardUrl || "";
  let endUrl = player.dataset.endUrl || "";

  const isTestMode = () => activeMode === "test";
  const getQuestions = () => (isTestMode() ? testQuestions : practiceQuestions);
  const getActiveIntroStage = () => (isTestMode() ? testIntroStage : practiceIntroStage);

  const persistTestProgress = async () => {
    if (!isTestMode() || !player.dataset.progressUrl) {
      return;
    }
    try {
      await fetch(player.dataset.progressUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ answers: submittedAnswers }),
      });
    } catch (error) {
      // Progress save should not block the test flow.
    }
  };

  const syncFullscreenTestUI = () => {
    const isFullscreenTestActive =
      isTestMode() &&
      testStarted &&
      document.fullscreenElement === player &&
      !finished;
    player.classList.toggle("is-fullscreen-test-active", isFullscreenTestActive);
    if (endTestButton) {
      if (isFullscreenTestActive) {
        endTestButton.removeAttribute("hidden");
      } else {
        endTestButton.setAttribute("hidden", "");
      }
    }
  };

  const showStage = (stage) => {
    [practiceIntroStage, testIntroStage, contextStage, questionStage, completeStage, loadingStage].forEach((node) => {
      if (!node) return;
      if (node === stage) {
        node.removeAttribute("hidden");
      } else {
        node.setAttribute("hidden", "");
      }
    });
  };

  const showFeedback = (message, type) => {
    if (!feedbackEl) return;
    feedbackEl.textContent = message;
    feedbackEl.className = `section-inline-feedback feedback-${type}`;
    feedbackEl.removeAttribute("hidden");
  };

  const hideFeedback = () => {
    if (!feedbackEl) return;
    feedbackEl.setAttribute("hidden", "");
    feedbackEl.textContent = "";
    feedbackEl.className = "section-inline-feedback";
  };

  const updateTimer = () => {
    if (!timerEl) return;
    if (!isTestMode()) {
      if (!practiceStarted) {
        const suggestedSeconds = practiceTotal ? Math.max(1, Math.round(timeLimitSeconds / practiceTotal)) : 0;
        timerEl.textContent = suggestedSeconds
          ? `Target pace ~${formatSeconds(suggestedSeconds)} per question`
          : "Start practice when ready";
        return;
      }
      const solvedCount = Math.max(practiceSolved, 1);
      const averageSeconds = Math.round(practiceElapsedSeconds / solvedCount);
      timerEl.textContent = `Average time ${formatSeconds(averageSeconds)} per solved question`;
      return;
    }
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    timerEl.textContent = `Time left ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  const updateProgress = () => {
    const questions = getQuestions();
    const total = questions.length;
    const displayIndex = Math.min(currentIndex + 1, total || 1);
    if (progressEl) {
      progressEl.textContent = `Question ${displayIndex} of ${total}`;
    }
    if (railProgressEl) {
      railProgressEl.textContent = `${displayIndex} / ${total || 1}`;
    }
    if (progressFillEl) {
      const progressPercent =
        !isTestMode()
          ? (practiceTotal ? Math.min(Math.round((practiceSolved / practiceTotal) * 100), 100) : 0)
          : total
            ? Math.max(1, Math.round((displayIndex / total) * 100))
            : 0;
      progressFillEl.style.width = `${progressPercent}%`;
      progressFillEl.parentElement?.setAttribute("aria-valuenow", String(progressPercent));
    }
    if (practiceProgressCopyEl && !isTestMode()) {
      practiceProgressCopyEl.textContent = `${practiceSolved} of ${practiceTotal} practice questions solved`;
    }
  };

  const syncModeUI = () => {
    if (practiceProgressWrapEl) {
      if (isTestMode()) {
        practiceProgressWrapEl.setAttribute("hidden", "");
      } else {
        practiceProgressWrapEl.removeAttribute("hidden");
      }
    }
    if (modeCopyEl) {
      modeCopyEl.textContent = isTestMode() ? (modeCopyEl.dataset.testCopy || "") : (modeCopyEl.dataset.practiceCopy || "");
    }
    if (railPhaseEl) {
      railPhaseEl.textContent = isTestMode() ? "Test" : "Practice";
    }
    modeButtons.forEach((button) => {
      const selected = button.dataset.playerMode === activeMode;
      button.classList.toggle("button", selected);
      button.classList.toggle("button-secondary", !selected);
      button.setAttribute("aria-selected", selected ? "true" : "false");
    });
  };

  const resetForMode = () => {
    currentIndex = 0;
    correctCount = 0;
    finished = false;
    testStarted = false;
    submittedAnswers.length = 0;
    if (timerInterval) {
      window.clearInterval(timerInterval);
      timerInterval = null;
    }
    if (practiceTimerInterval) {
      window.clearInterval(practiceTimerInterval);
      practiceTimerInterval = null;
    }
    if (isTestMode()) {
      practiceStarted = false;
      practiceElapsedSeconds = 0;
    }
    hideFeedback();
    syncModeUI();
    syncFullscreenTestUI();
    updateProgress();
    updateTimer();
    showStage(getActiveIntroStage());
  };

  const loadTestSetup = async () => {
    if (testSetupLoaded) {
      return true;
    }
    const response = await fetch(player.dataset.testSetupUrl, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not start test mode.");
    }
    testQuestions = payload.previews || [];
    player.dataset.submitUrl = payload.submitUrl || "";
    player.dataset.progressUrl = payload.progressUrl || "";
    player.dataset.attemptId = payload.attemptId || "";
    player.dataset.endUrl = payload.endUrl || "";
    endUrl = payload.endUrl || "";
    testSetupLoaded = true;
    return true;
  };

  const syncPracticeProgress = async () => {
    if (!player.dataset.practiceProgressUrl || !sectionKey) {
      return;
    }
    try {
      await fetch(player.dataset.practiceProgressUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ assessment_type: assessmentType, section_type: sectionKey, solved_increment: 1 }),
      });
    } catch (error) {
      // Practice progress sync is helpful but should not block the player flow.
    }
  };

  const finishPlayer = async () => {
    if (finished) {
      return;
    }
    finished = true;
    syncFullscreenTestUI();
    if (timerInterval) {
      window.clearInterval(timerInterval);
    }
    if (practiceTimerInterval) {
      window.clearInterval(practiceTimerInterval);
    }
    if (completeSummaryEl) {
      const questions = getQuestions();
      const base = `You answered ${correctCount} out of ${questions.length} correctly.`;
      completeSummaryEl.textContent =
        !isTestMode()
          ? `${base} Practice mode shows immediate feedback after each answer.`
          : `${base} Test mode finished without per-question feedback.`;
    }
    hideFeedback();
    if (isTestMode() && player.dataset.submitUrl) {
      window.showPageLoader?.();
      if (completeSummaryEl) {
        completeSummaryEl.textContent = "Saving your section test result...";
      }
      try {
        const response = await fetch(player.dataset.submitUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify({ answers: submittedAnswers }),
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || "Could not save the section test result.");
        }
        if (completeSummaryEl) {
          completeSummaryEl.textContent = `Final section score: ${result.section_score}.`;
        }
        if (player.dataset.dashboardUrl) {
          window.location.assign(player.dataset.dashboardUrl);
          return;
        }
      } catch (error) {
        window.hidePageLoader?.();
        if (completeSummaryEl) {
          completeSummaryEl.textContent = error.message || "Could not save the section test result.";
        }
      }
    }
    showStage(completeStage);
  };

  const redirectToPracticeAfterEnd = async () => {
    const target = endUrl ? (returnUrl ? `${endUrl}?next=${encodeURIComponent(returnUrl)}` : endUrl) : returnUrl;
    if (!target) {
      finishPlayer();
      return;
    }
    showStage(loadingStage);
    window.showPageLoader?.();
    hideFeedback();
    if (timerInterval) {
      window.clearInterval(timerInterval);
    }
    try {
      if (document.fullscreenElement && document.exitFullscreen) {
        await document.exitFullscreen();
      }
    } catch (error) {
      // Even if fullscreen exit fails, continue to redirect away from the player.
    }
    window.setTimeout(() => {
      window.location.replace(target);
    }, 180);
  };

  const renderQuestion = () => {
    const questions = getQuestions();
    const item = questions[currentIndex];
    if (!item) {
      finishPlayer();
      return;
    }

    updateProgress();

    if (seedEl) {
      seedEl.textContent = item.seed || "";
    }
    if (contextEl) {
      if (isTestMode() && item.reveal_mode === "question_only") {
        contextEl.innerHTML = "";
        const hiddenPrompt = document.createElement("p");
        hiddenPrompt.className = "muted";
        hiddenPrompt.textContent = "Question hidden. Click to reveal and answer from memory.";
        contextEl.appendChild(hiddenPrompt);
      } else {
        renderContext(contextEl, item);
      }
    }
    if (questionEl) {
      questionEl.textContent = item.question_text || item.summary || "";
    }
    if (optionsEl) {
      optionsEl.innerHTML = "";
      (item.options || []).forEach((option) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "answer-option";
        button.textContent = option;
        button.addEventListener("click", () => {
          if (!isTestMode()) {
            optionsEl.querySelectorAll(".answer-option").forEach((node) => {
              node.classList.remove("is-selected-correct", "is-selected-wrong");
            });
          }
          const selected = String(option);
          const isCorrect = selected === String(item.correct_answer || "");
          if (isCorrect) {
            correctCount += 1;
          }

          if (!isTestMode()) {
            if (isCorrect) {
              button.classList.add("is-selected-correct");
              practiceSolved += 1;
              syncPracticeProgress();
              updateProgress();
              showFeedback("Correct.", "correct");
              if (feedbackTimeout) {
                window.clearTimeout(feedbackTimeout);
              }
              feedbackTimeout = window.setTimeout(() => {
                hideFeedback();
                currentIndex += 1;
                renderQuestion();
              }, 900);
            } else {
              button.classList.add("is-selected-wrong");
              showFeedback("Wrong. Try again.", "wrong");
            }
          } else {
            const answerRow = { question_index: currentIndex, selected_option: selected };
            const existingIndex = submittedAnswers.findIndex((row) => row.question_index === currentIndex);
            if (existingIndex >= 0) {
              submittedAnswers[existingIndex] = answerRow;
            } else {
              submittedAnswers.push(answerRow);
            }
            persistTestProgress();
            currentIndex += 1;
            renderQuestion();
          }
        });
        optionsEl.appendChild(button);
      });
    }

    if (contextHelperEl) {
      contextHelperEl.textContent =
        isTestMode() && item.reveal_mode === "question_only"
          ? "Click to reveal the question."
          : "Click the context card to reveal the question.";
    }
    if (isTestMode()) {
      showStage(contextStage);
      return;
    }
    if (item.reveal_mode === "question_only") {
      showStage(questionStage);
      return;
    }
    showStage(contextStage);
  };

  contextStage?.addEventListener("click", () => {
    showStage(questionStage);
  });

  endTestButton?.addEventListener("click", () => {
    redirectToPracticeAfterEnd();
  });

  document.addEventListener("fullscreenchange", syncFullscreenTestUI);

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextMode = button.dataset.playerMode || "practice";
      if (nextMode === activeMode) {
        return;
      }
      activeMode = nextMode;
      player.dataset.mode = activeMode;
      resetForMode();
    });
  });

  fullscreenStartButton?.addEventListener("click", async () => {
    window.showPageLoader?.();
    try {
      await loadTestSetup();
    } catch (error) {
      window.hidePageLoader?.();
      showFeedback(error.message || "Could not start test mode.", "wrong");
      return;
    }
    const enteredFullscreen = await requestFullscreenFor(player);
    if (!enteredFullscreen) {
      window.hidePageLoader?.();
      showFeedback("Fullscreen is required to start test mode.", "wrong");
      return;
    }
    activeMode = "test";
    player.dataset.mode = activeMode;
    currentIndex = 0;
    correctCount = 0;
    remainingSeconds = timeLimitSeconds;
    finished = false;
    testStarted = true;
    hideFeedback();
    syncModeUI();
    syncFullscreenTestUI();
    updateProgress();
    updateTimer();
    timerInterval = window.setInterval(() => {
      remainingSeconds -= 1;
      updateTimer();
      if (remainingSeconds <= 0) {
        finishPlayer();
      }
    }, 1000);
    renderQuestion();
    await waitForNextPaint();
    await waitForNextPaint();
    window.hidePageLoader?.();
  });

  practiceStartButton?.addEventListener("click", () => {
    if (practiceStarted) {
      return;
    }
    activeMode = "practice";
    player.dataset.mode = activeMode;
    practiceStarted = true;
    practiceElapsedSeconds = 0;
    submittedAnswers.length = 0;
    syncModeUI();
    updateProgress();
    updateTimer();
    practiceTimerInterval = window.setInterval(() => {
      practiceElapsedSeconds += 1;
      updateTimer();
    }, 1000);
    renderQuestion();
  });

  syncModeUI();
  updateProgress();
  updateTimer();
  showStage(getActiveIntroStage());

  window.addEventListener("beforeunload", () => {
    if (!isTestMode() || !player.dataset.progressUrl || finished) return;
    fetch(player.dataset.progressUrl, {
      method: "POST",
      keepalive: true,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ answers: submittedAnswers }),
    });
  });
}

function formatSeconds(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function initFullTestPlayer() {
  const player = document.querySelector("[data-full-test-player]");
  const dataScript = document.getElementById("full-test-data");

  if (!player || !dataScript) {
    return;
  }

  const sections = JSON.parse(dataScript.textContent || "[]");
  let sectionIndex = 0;
  let phase = "intro";
  let questionIndex = 0;
  let remainingSeconds = 0;
  let timerInterval = null;
  let activeQuestion = null;
  let currentSectionRuntime = null;
  const collectedTestAnswers = [];
  let isSubmitting = false;
  let shouldAdvanceDirectlyToNextSection = false;

  const timerEl = player.querySelector("[data-full-timer]");
  const titleEl = player.querySelector("[data-full-section-title]");
  const descriptionEl = player.querySelector("[data-full-section-description]");
  const instructionEl = player.querySelector("[data-full-instruction]");
  const phaseLabelEl = player.querySelector("[data-full-phase-label]");
  const railSectionEl = player.querySelector("[data-full-rail-section]");
  const railPhaseEl = player.querySelector("[data-full-rail-phase]");
  const railProgressEl = player.querySelector("[data-full-rail-progress]");
  const railProgressFillEl = player.querySelector("[data-full-rail-progress-fill]");
  const feedbackEl = player.querySelector("[data-full-feedback]");
  const contextEl = player.querySelector("[data-full-context]");
  const questionEl = player.querySelector("[data-full-question]");
  const optionsEl = player.querySelector("[data-full-options]");
  const inlineFeedbackEl = player.querySelector("[data-full-inline-feedback]");
  const startButton = player.querySelector("[data-full-start]");
  const fullscreenStartButton = player.querySelector("[data-full-fullscreen-start]");
  const nextPhaseButton = player.querySelector("[data-full-next-phase]");
  const skipPracticeButton = player.querySelector("[data-full-skip-practice]");
  const endTestButton = player.querySelector("[data-full-end-test]");
  const endModalEl = player.querySelector("[data-full-end-modal]");
  const endModalCancelButton = player.querySelector("[data-full-end-cancel]");
  const endModalConfirmButton = player.querySelector("[data-full-end-confirm]");

  const persistFullTestProgress = async () => {
    if (!player.dataset.progressUrl) {
      return;
    }
    try {
      await fetch(player.dataset.progressUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ sections: collectedTestAnswers }),
      });
    } catch (error) {
      // Progress save should not block the full test flow.
    }
  };

  const updateEndTestButton = () => {
    if (!endTestButton) return;
    if (phase === "practice" || phase === "test") {
      endTestButton.removeAttribute("hidden");
    } else {
      endTestButton.setAttribute("hidden", "");
    }
  };
  const updateSkipPracticeButton = () => {
    if (!skipPracticeButton) return;
    if (phase === "practice") {
      skipPracticeButton.removeAttribute("hidden");
    } else {
      skipPracticeButton.setAttribute("hidden", "");
    }
  };
  const sectionCompleteLabelEl = player.querySelector("[data-full-section-complete-label]");
  const sectionCompleteTitleEl = player.querySelector("[data-full-section-complete-title]");
  const sectionCompleteCopyEl = player.querySelector("[data-full-section-complete-copy]");
  const completeSummaryEl = player.querySelector("[data-full-complete-summary]");

  const introStage = player.querySelector('[data-full-stage="intro"]');
  const fullscreenStage = player.querySelector('[data-full-stage="fullscreen"]');
  const contextStage = player.querySelector('[data-full-stage="context"]');
  const questionStage = player.querySelector('[data-full-stage="question"]');
  const sectionCompleteStage = player.querySelector('[data-full-stage="section-complete"]');
  const completeStage = player.querySelector('[data-full-stage="complete"]');

  const allStages = [introStage, fullscreenStage, contextStage, questionStage, sectionCompleteStage, completeStage];

  const getCurrentSection = () => sections[sectionIndex];
  const getCurrentQuestionCount = () =>
    phase === "practice"
      ? currentSectionRuntime?.practice_questions?.length || getCurrentSection()?.practice_count || 0
      : currentSectionRuntime?.test_questions?.length || getCurrentSection()?.test_count || 0;
  const getCurrentSectionAnswers = () => {
    const sectionId = getCurrentSection()?.section_id;
    if (!sectionId) {
      return null;
    }
    let entry = collectedTestAnswers.find((row) => row.section_id === sectionId);
    if (!entry) {
      entry = { section_id: sectionId, answers: [] };
      collectedTestAnswers.push(entry);
    }
    return entry;
  };
  const getActiveQuestions = () => {
    if (!currentSectionRuntime) {
      return [];
    }
    return phase === "practice" ? currentSectionRuntime.practice_questions || [] : currentSectionRuntime.test_questions || [];
  };
  const getRailPhaseLabel = () => {
    if (phase === "practice") {
      return "Practice";
    }
    if (phase === "test") {
      return "Timed test";
    }
    if (phase === "test-intro") {
      return "Ready";
    }
    return "Intro";
  };
  const updateRail = () => {
    const section = getCurrentSection();
    const currentQuestionCount = getCurrentQuestionCount();
    let progressLabel = `${Math.min(sectionIndex + 1, sections.length)} / ${sections.length}`;
    let progressRatio = sections.length ? (sectionIndex + 1) / sections.length : 0;

    if ((phase === "practice" || phase === "test") && currentQuestionCount > 0) {
      const currentStep = Math.min(questionIndex + 1, currentQuestionCount);
      progressLabel = `${currentStep} / ${currentQuestionCount}`;
      progressRatio = currentStep / currentQuestionCount;
    }

    if (railSectionEl) {
      railSectionEl.textContent = section?.title || "Section";
    }
    if (railPhaseEl) {
      railPhaseEl.textContent = getRailPhaseLabel();
    }
    if (railProgressEl) {
      railProgressEl.textContent = progressLabel;
    }
    if (railProgressFillEl) {
      railProgressFillEl.style.width = `${Math.max(0, Math.min(progressRatio, 1)) * 100}%`;
    }
  };

  const showStage = (stage) => {
    updateSkipPracticeButton();
    updateRail();
    allStages.forEach((node) => {
      if (!node) return;
      if (node === stage) {
        node.removeAttribute("hidden");
      } else {
        node.setAttribute("hidden", "");
      }
    });
  };

  const showFeedback = (message, type) => {
    if (!feedbackEl) return;
    feedbackEl.textContent = message;
    feedbackEl.className = `feedback-banner feedback-${type}`;
    feedbackEl.removeAttribute("hidden");
  };

  const hideFeedback = () => {
    if (!feedbackEl) return;
    feedbackEl.setAttribute("hidden", "");
    feedbackEl.textContent = "";
    feedbackEl.className = "feedback-banner";
  };

  const hideInlineFeedback = () => {
    if (!inlineFeedbackEl) return;
    inlineFeedbackEl.setAttribute("hidden", "");
    inlineFeedbackEl.textContent = "";
    inlineFeedbackEl.className = "section-inline-feedback full-test-inline-feedback";
  };

  const showInlineFeedback = (message, type) => {
    if (!inlineFeedbackEl) return;
    inlineFeedbackEl.textContent = message;
    inlineFeedbackEl.className = `section-inline-feedback full-test-inline-feedback feedback-${type}`;
    inlineFeedbackEl.removeAttribute("hidden");
  };

  const openEndModal = () => {
    if (!endModalEl) {
      return;
    }
    endModalEl.removeAttribute("hidden");
    document.body.classList.add("has-open-modal");
    endModalConfirmButton?.focus();
  };

  const closeEndModal = () => {
    if (!endModalEl) {
      return;
    }
    endModalEl.setAttribute("hidden", "");
    document.body.classList.remove("has-open-modal");
    endTestButton?.focus();
  };

  const updateTimer = () => {
    if (!timerEl) return;
    if (phase !== "test") {
      timerEl.setAttribute("hidden", "");
      updateRail();
      return;
    }
    timerEl.removeAttribute("hidden");
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    timerEl.textContent = `• ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    updateRail();
  };

  const stopTimer = () => {
    if (timerInterval) {
      window.clearInterval(timerInterval);
      timerInterval = null;
    }
  };

  const startTimer = () => {
    stopTimer();
    remainingSeconds = getCurrentSection()?.time_limit_seconds || 0;
    updateTimer();
    timerInterval = window.setInterval(() => {
      remainingSeconds -= 1;
      updateTimer();
      if (remainingSeconds <= 0) {
        finishPhase();
      }
    }, 1000);
  };

  const loadSectionRuntime = async (force = false) => {
    const section = getCurrentSection();
    if (!section) {
      throw new Error("Could not load the current test section.");
    }
    if (!force && currentSectionRuntime?.section_id === section.section_id) {
      return currentSectionRuntime;
    }
    const params = new URLSearchParams({
      section_index: String(sectionIndex),
    });
    const response = await fetch(`${player.dataset.sectionUrl}?${params.toString()}`, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load the full test section.");
    }
    currentSectionRuntime = payload;
    return payload;
  };

  const renderQuestion = async () => {
    await loadSectionRuntime();
    const questions = getActiveQuestions();
    if (questionIndex >= questions.length) {
      await finishPhase();
      return;
    }

    try {
      activeQuestion = questions[questionIndex];
      hideFeedback();
      hideInlineFeedback();
      if (contextEl) renderContext(contextEl, activeQuestion);
      if (questionEl) questionEl.textContent = activeQuestion.question_text || activeQuestion.summary || "";
      if (optionsEl) {
        optionsEl.innerHTML = "";
        (activeQuestion.options || []).forEach((option) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "answer-option";
          button.textContent = option;
          button.addEventListener("click", () => {
            const selected = String(option);
            const isCorrect = selected === String(activeQuestion.correct_answer || "");

            if (phase === "practice") {
              const answerButtons = Array.from(optionsEl.querySelectorAll(".answer-option"));
              answerButtons.forEach((node) => {
                node.disabled = true;
                node.classList.remove("is-selected-correct", "is-selected-wrong", "is-correct-answer");
              });
              answerButtons.forEach((node) => {
                const nodeText = String(node.textContent || "");
                if (nodeText === selected) {
                  node.classList.add(isCorrect ? "is-selected-correct" : "is-selected-wrong");
                }
                if (nodeText === String(activeQuestion.correct_answer || "")) {
                  node.classList.add("is-correct-answer");
                }
              });
              if (isCorrect) {
                showInlineFeedback("Correct.", "correct");
                window.setTimeout(() => {
                  hideInlineFeedback();
                  questionIndex += 1;
                  void renderQuestion();
                }, 900);
              } else {
                showInlineFeedback(`Wrong. The correct answer is ${activeQuestion.correct_answer || ""}.`, "wrong");
                window.setTimeout(() => {
                  hideInlineFeedback();
                  questionIndex += 1;
                  void renderQuestion();
                }, 1200);
              }
              return;
            }

            const entry = getCurrentSectionAnswers();
            const answerRow = { question_index: questionIndex, selected_option: selected };
            if (entry) {
              const existingIndex = entry.answers.findIndex((row) => row.question_index === questionIndex);
              if (existingIndex >= 0) {
                entry.answers[existingIndex] = answerRow;
              } else {
                entry.answers.push(answerRow);
              }
            }

            persistFullTestProgress();
            questionIndex += 1;
            void renderQuestion();
          });
          optionsEl.appendChild(button);
        });
      }
      if (activeQuestion.reveal_mode === "question_only") {
        showStage(questionStage);
      } else {
        showStage(contextStage);
      }
    } catch (error) {
      if (completeSummaryEl) {
        completeSummaryEl.textContent = error.message || "There was a problem loading the test question.";
      }
      showStage(completeStage);
    }
  };

  const renderIntro = () => {
    const section = getCurrentSection();
    if (!section) {
      showStage(completeStage);
      return;
    }

    stopTimer();
    hideFeedback();
    updateTimer();

    if (titleEl) titleEl.textContent = section.title;
    if (descriptionEl) descriptionEl.textContent = section.description;
    if (instructionEl) instructionEl.textContent = section.instruction;
    if (phaseLabelEl) {
      phaseLabelEl.textContent = phase === "test-intro" ? "Timed test" : "Section intro";
    }
    if (startButton) {
      startButton.textContent = "Enter fullscreen and start full test";
    }
    updateRail();
    showStage(introStage);
  };

  const renderFullscreenStage = () => {
    stopTimer();
    hideFeedback();
    updateTimer();
    showStage(fullscreenStage);
  };

  const startSectionPractice = async () => {
    hideFeedback();
    hideInlineFeedback();
    questionIndex = 0;
    phase = "practice";
    currentSectionRuntime = null;
    shouldAdvanceDirectlyToNextSection = false;
    updateEndTestButton();
    updateSkipPracticeButton();
    updateTimer();
    await loadSectionRuntime(true);
    await renderQuestion();
    await waitForNextPaint();
    await waitForNextPaint();
  };

  const submitCurrentSection = async () => {
    const section = getCurrentSection();
    if (!section?.section_id || !player.dataset.sectionSubmitUrl) {
      return;
    }
    const entry = getCurrentSectionAnswers();
    const response = await fetch(player.dataset.sectionSubmitUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ section_id: section.section_id, answers: entry?.answers || [] }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not save the completed section.");
    }
  };

  const finishPhase = async () => {
    stopTimer();
    const section = getCurrentSection();
    if (!section) {
      showStage(completeStage);
      return;
    }

    if (phase === "practice") {
      phase = "test-intro";
      questionIndex = 0;
      shouldAdvanceDirectlyToNextSection = false;
      updateEndTestButton();
      updateSkipPracticeButton();
      if (sectionCompleteLabelEl) sectionCompleteLabelEl.textContent = "Practice complete";
      if (sectionCompleteTitleEl) sectionCompleteTitleEl.textContent = `${section.title} practice complete`;
      if (sectionCompleteCopyEl) sectionCompleteCopyEl.textContent = "Next, start the timed test for this section.";
      if (nextPhaseButton) nextPhaseButton.textContent = "Start timed test";
      showStage(sectionCompleteStage);
      return;
    }

    window.showPageLoader?.();
    try {
      await submitCurrentSection();
    } catch (error) {
      window.hidePageLoader?.();
      if (completeSummaryEl) {
        completeSummaryEl.textContent = error.message || "Could not save the completed section.";
      }
      showStage(completeStage);
      return;
    }

    sectionIndex += 1;
    questionIndex = 0;
    currentSectionRuntime = null;
    if (sectionIndex >= sections.length) {
      await submitFullTest();
      return;
    }

    phase = "intro";
    shouldAdvanceDirectlyToNextSection = true;
    if (sectionCompleteLabelEl) sectionCompleteLabelEl.textContent = "Section complete";
    if (sectionCompleteTitleEl) sectionCompleteTitleEl.textContent = `${section.title} test complete`;
    if (sectionCompleteCopyEl) sectionCompleteCopyEl.textContent = "Continue directly into the next section practice flow.";
    if (nextPhaseButton) nextPhaseButton.textContent = "Next section";
    showStage(sectionCompleteStage);
    window.hidePageLoader?.();
  };

  startButton?.addEventListener("click", async () => {
    window.setButtonLoading?.(startButton);
    window.showPageLoader?.();
    const enteredFullscreen = await requestFullscreenFor(player);
    if (!enteredFullscreen) {
      window.clearButtonLoading?.(startButton);
      window.hidePageLoader?.();
      showFeedback("Fullscreen is required to start the full test.", "wrong");
      return;
    }
    await startSectionPractice();
    window.clearButtonLoading?.(startButton);
    window.hidePageLoader?.();
  });

  fullscreenStartButton?.addEventListener("click", async () => {
    window.setButtonLoading?.(fullscreenStartButton);
    window.showPageLoader?.();
    const enteredFullscreen = await requestFullscreenFor(player);
    if (!enteredFullscreen) {
      window.clearButtonLoading?.(fullscreenStartButton);
      window.hidePageLoader?.();
      showFeedback("Fullscreen is required to start timed test mode.", "wrong");
      return;
    }
    hideFeedback();
    questionIndex = 0;
    phase = "test";
    currentSectionRuntime = null;
    updateEndTestButton();
    await loadSectionRuntime(true);
    startTimer();
    await renderQuestion();
    await waitForNextPaint();
    await waitForNextPaint();
    window.clearButtonLoading?.(fullscreenStartButton);
    window.hidePageLoader?.();
  });

  nextPhaseButton?.addEventListener("click", async () => {
    window.setButtonLoading?.(nextPhaseButton);
    if (phase === "test-intro") {
      if (document.fullscreenElement) {
        questionIndex = 0;
        phase = "test";
        currentSectionRuntime = null;
        updateEndTestButton();
        window.showPageLoader?.();
        await loadSectionRuntime(true);
        startTimer();
        await renderQuestion();
        await waitForNextPaint();
        await waitForNextPaint();
        window.clearButtonLoading?.(nextPhaseButton);
        window.hidePageLoader?.();
        return;
      }
      window.clearButtonLoading?.(nextPhaseButton);
      renderFullscreenStage();
      return;
    }
    if (shouldAdvanceDirectlyToNextSection) {
      window.showPageLoader?.();
      if (!document.fullscreenElement) {
        const enteredFullscreen = await requestFullscreenFor(player);
        if (!enteredFullscreen) {
          window.clearButtonLoading?.(nextPhaseButton);
          window.hidePageLoader?.();
          showFeedback("Fullscreen is required to continue into the next section.", "wrong");
          return;
        }
      }
      await startSectionPractice();
      window.clearButtonLoading?.(nextPhaseButton);
      window.hidePageLoader?.();
      return;
    }
    updateEndTestButton();
    updateSkipPracticeButton();
    window.clearButtonLoading?.(nextPhaseButton);
    renderIntro();
  });

  skipPracticeButton?.addEventListener("click", async () => {
    if (phase !== "practice") {
      return;
    }
    window.setButtonLoading?.(skipPracticeButton);
    window.showPageLoader?.();
    hideFeedback();
    questionIndex += 1;
    await renderQuestion();
    await waitForNextPaint();
    window.clearButtonLoading?.(skipPracticeButton);
    window.hidePageLoader?.();
  });

  contextStage?.addEventListener("click", () => {
    showStage(questionStage);
  });

  async function submitFullTest() {
    if (isSubmitting) {
      return;
    }
    isSubmitting = true;
    stopTimer();
    hideFeedback();
    if (!player.dataset.submitUrl) {
      showStage(completeStage);
      return;
    }

    try {
      window.showPageLoader?.();
      const response = await fetch(player.dataset.submitUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ sections: collectedTestAnswers }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Submission failed.");
      }
      if (completeSummaryEl) {
        const breakdown = (result.section_scores || [])
          .map((item) => `${item.section_type}: ${item.score}`)
          .join(" | ");
        completeSummaryEl.textContent = `Final score: ${result.overall_score}. ${breakdown}`;
      }
      if (player.dataset.dashboardUrl) {
        window.location.assign(player.dataset.dashboardUrl);
        return;
      }
    } catch (error) {
      window.hidePageLoader?.();
      if (completeSummaryEl) {
        completeSummaryEl.textContent = error.message || "There was a problem submitting the test.";
      }
      isSubmitting = false;
    }

    showStage(completeStage);
  }

  endTestButton?.addEventListener("click", () => {
    openEndModal();
  });

  endModalCancelButton?.addEventListener("click", () => {
    closeEndModal();
  });

  endModalEl?.addEventListener("click", (event) => {
    if (event.target === endModalEl) {
      closeEndModal();
    }
  });

  endModalConfirmButton?.addEventListener("click", () => {
    closeEndModal();
    window.setButtonLoading?.(endTestButton);
    window.showPageLoader?.();
    void submitFullTest().finally(() => {
      window.clearButtonLoading?.(endTestButton);
    });
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && endModalEl && !endModalEl.hasAttribute("hidden")) {
      closeEndModal();
    }
  });

  window.addEventListener("beforeunload", () => {
    if (isSubmitting || !player.dataset.progressUrl || phase === "complete") return;
    fetch(player.dataset.progressUrl, {
      method: "POST",
      keepalive: true,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify({ sections: collectedTestAnswers }),
    });
  });

  renderIntro();
  updateRail();
}

function renderContext(container, item) {
  container.innerHTML = "";
  const appendContinuePrompt = () => {};

  const addParagraph = (text) => {
    const p = document.createElement("p");
    p.textContent = text;
    p.style.fontWeight = "700";
    container.appendChild(p);
  };

  if (item.context_kind === "statements") {
    (item.context_lines || []).forEach(addParagraph);
    appendContinuePrompt();
    return;
  }

  if (item.instruction) {
    const intro = document.createElement("p");
    intro.className = "muted";
    intro.textContent = item.instruction;
    container.appendChild(intro);
  }

  if (item.context_kind === "pairs") {
    const pairGrid = document.createElement("div");
    pairGrid.className = "pair-grid";
    (item.pairs || []).forEach((pair) => {
      const pairCell = document.createElement("div");
      pairCell.className = "pair-cell";
      const topLetter = document.createElement("span");
      topLetter.className = "pair-letter";
      topLetter.textContent = String(pair.left || "");
      const bottomLetter = document.createElement("span");
      bottomLetter.className = "pair-letter";
      bottomLetter.textContent = String(pair.right || "");
      pairCell.appendChild(topLetter);
      pairCell.appendChild(bottomLetter);
      pairGrid.appendChild(pairCell);
    });
    container.appendChild(pairGrid);
    appendContinuePrompt();
    return;
  }

  if (item.context_kind === "numbers") {
    const row = document.createElement("div");
    row.className = "number-row";
    (item.numbers || []).forEach((number) => {
      const chip = document.createElement("div");
      chip.className = "number-chip";
      chip.textContent = String(number);
      row.appendChild(chip);
    });
    container.appendChild(row);
    appendContinuePrompt();
    return;
  }

  if (item.context_kind === "words") {
    const row = document.createElement("div");
    row.className = "word-row";
    (item.words || []).forEach((word) => {
      const chip = document.createElement("div");
      chip.className = "word-chip";
      chip.textContent = String(word);
      row.appendChild(chip);
    });
    container.appendChild(row);
    appendContinuePrompt();
    return;
  }

  if (item.context_kind === "letter_pairs") {
    const pairsWrap = document.createElement("div");
    pairsWrap.className = "spatial-pairs-wrap";
    (item.letter_pairs || []).forEach((pair) => {
      const pairEl = document.createElement("div");
      pairEl.className = "spatial-pair";
      pairEl.appendChild(renderLetterSvg(pair.letter, false));
      pairEl.appendChild(renderLetterSvg(pair.letter, !pair.same));
      pairsWrap.appendChild(pairEl);
    });
    container.appendChild(pairsWrap);
    return;
  }

  addParagraph(item.summary || "");
  appendContinuePrompt();
}

async function requestFullscreenFor(element) {
  if (document.fullscreenElement) {
    return true;
  }
  if (!element?.requestFullscreen) {
    return false;
  }
  try {
    await element.requestFullscreen();
    return true;
  } catch (error) {
    return false;
  }
}

function waitForNextPaint() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(resolve);
    });
  });
}

function renderLetterSvg(letter, mirrored) {
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("class", "shape-svg");

  const text = document.createElementNS(svgNS, "text");
  text.setAttribute("x", "50");
  text.setAttribute("y", "78");
  text.setAttribute("text-anchor", "middle");
  text.setAttribute("font-size", "80");
  text.setAttribute("font-family", "Georgia, serif");
  text.setAttribute("font-weight", "bold");
  text.setAttribute("fill", "#0f766e");
  if (mirrored) {
    text.setAttribute("transform", "scale(-1,1) translate(-100,0)");
  }
  text.textContent = letter;
  svg.appendChild(text);
  return svg;
}

function getCookie(name) {
  const cookieValue = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
  return cookieValue ? decodeURIComponent(cookieValue) : "";
}

function dismissFlash(msg) {
  msg.classList.add("flash-hiding");
  setTimeout(() => msg.remove(), 400);
}

document.querySelectorAll(".flash-message").forEach((msg) => {
  msg.querySelector(".flash-close")?.addEventListener("click", () => dismissFlash(msg));
  setTimeout(() => dismissFlash(msg), 5000);
});
