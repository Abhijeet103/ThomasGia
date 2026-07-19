document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const role = body.dataset.role;
  if (role) {
    body.classList.add(`role-context-${role}`);
  }

  initSectionHelpToggle();
  initSectionPlayer();
  initFullTestPlayer();
});

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
  const dataScript = document.getElementById("section-question-data");

  if (!player || !dataScript) {
    return;
  }

  const questions = JSON.parse(dataScript.textContent || "[]");
  let currentIndex = 0;
  let correctCount = 0;
  let feedbackTimeout = null;
  const mode = player.dataset.mode || "practice";
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

  const seedEl = player.querySelector("[data-test-seed]");
  const progressEl = player.querySelector("[data-test-progress]");
  const progressFillEl = player.querySelector("[data-test-progress-fill]");
  const practiceProgressCopyEl = player.querySelector("[data-practice-progress-copy]");
  const timerEl = player.querySelector("[data-test-timer]");
  const feedbackEl = player.querySelector("[data-feedback-banner]");
  const completeSummaryEl = player.querySelector("[data-complete-summary]");
  const contextEl = player.querySelector("[data-test-context]");
  const questionEl = player.querySelector("[data-test-question]");
  const optionsEl = player.querySelector("[data-test-options]");

  const contextStage = player.querySelector('[data-test-stage="context"]');
  const questionStage = player.querySelector('[data-test-stage="question"]');
  const completeStage = player.querySelector('[data-test-stage="complete"]');
  const introStage = player.querySelector('[data-test-stage="intro"]');
  const fullscreenStartButton = player.querySelector("[data-test-fullscreen-start]");
  const practiceStartButton = player.querySelector("[data-test-practice-start]");
  const endTestButton = player.querySelector("[data-test-end]");

  const syncFullscreenTestUI = () => {
    const isFullscreenTestActive =
      mode === "test" &&
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
    [introStage, contextStage, questionStage, completeStage].forEach((node) => {
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
    if (mode !== "test") {
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
    const total = questions.length;
    const displayIndex = Math.min(currentIndex + 1, total || 1);
    if (progressEl) {
      progressEl.textContent = `Question ${displayIndex} of ${total}`;
    }
    if (progressFillEl) {
      const progressPercent =
        mode === "practice"
          ? (practiceTotal ? Math.min(Math.round((practiceSolved / practiceTotal) * 100), 100) : 0)
          : total
            ? Math.max(1, Math.round((displayIndex / total) * 100))
            : 0;
      progressFillEl.style.width = `${progressPercent}%`;
      progressFillEl.parentElement?.setAttribute("aria-valuenow", String(progressPercent));
    }
    if (practiceProgressCopyEl && mode === "practice") {
      practiceProgressCopyEl.textContent = `${practiceSolved} of ${practiceTotal} practice questions solved`;
    }
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
      const base = `You answered ${correctCount} out of ${questions.length} correctly.`;
      completeSummaryEl.textContent =
        mode === "practice"
          ? `${base} Practice mode shows immediate feedback after each answer.`
          : `${base} Test mode finished without per-question feedback.`;
    }
    hideFeedback();
    if (mode === "test" && player.dataset.submitUrl) {
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
        if (completeSummaryEl) {
          completeSummaryEl.textContent = error.message || "Could not save the section test result.";
        }
      }
    }
    showStage(completeStage);
  };

  const renderQuestion = () => {
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
      renderContext(contextEl, item);
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
          if (mode === "practice") {
            optionsEl.querySelectorAll(".answer-option").forEach((node) => {
              node.classList.remove("is-selected-correct", "is-selected-wrong");
            });
          }
          const selected = String(option);
          const isCorrect = selected === String(item.correct_answer || "");
          if (isCorrect) {
            correctCount += 1;
          }

          if (mode === "practice") {
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
            currentIndex += 1;
            renderQuestion();
          }
        });
        optionsEl.appendChild(button);
      });
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

  if (mode === "test" && timerEl && remainingSeconds > 0) {
    endTestButton?.addEventListener("click", () => {
      finishPlayer();
    });
    document.addEventListener("fullscreenchange", syncFullscreenTestUI);
    fullscreenStartButton?.addEventListener("click", async () => {
      const enteredFullscreen = await requestFullscreenFor(player);
      if (!enteredFullscreen) {
        showFeedback("Fullscreen is required to start test mode.", "wrong");
        return;
      }
      testStarted = true;
      hideFeedback();
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
    });
    syncFullscreenTestUI();
    showStage(introStage);
    return;
  }

  practiceStartButton?.addEventListener("click", () => {
    if (practiceStarted) {
      return;
    }
    practiceStarted = true;
    practiceElapsedSeconds = 0;
    updateProgress();
    updateTimer();
    practiceTimerInterval = window.setInterval(() => {
      practiceElapsedSeconds += 1;
      updateTimer();
    }, 1000);
    renderQuestion();
  });

  updateProgress();
  updateTimer();
  showStage(introStage);
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
  const collectedTestAnswers = [];
  let isSubmitting = false;

  const timerEl = player.querySelector("[data-full-timer]");
  const titleEl = player.querySelector("[data-full-section-title]");
  const descriptionEl = player.querySelector("[data-full-section-description]");
  const instructionEl = player.querySelector("[data-full-instruction]");
  const phaseLabelEl = player.querySelector("[data-full-phase-label]");
  const feedbackEl = player.querySelector("[data-full-feedback]");
  const contextEl = player.querySelector("[data-full-context]");
  const questionEl = player.querySelector("[data-full-question]");
  const optionsEl = player.querySelector("[data-full-options]");
  const startButton = player.querySelector("[data-full-start]");
  const fullscreenStartButton = player.querySelector("[data-full-fullscreen-start]");
  const nextPhaseButton = player.querySelector("[data-full-next-phase]");
  const endTestButton = player.querySelector("[data-full-end-test]");

  const updateEndTestButton = () => {
    if (!endTestButton) return;
    if (phase === "practice" || phase === "test") {
      endTestButton.removeAttribute("hidden");
    } else {
      endTestButton.setAttribute("hidden", "");
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
    phase === "practice" ? getCurrentSection()?.practice_count || 0 : getCurrentSection()?.test_count || 0;

  const showStage = (stage) => {
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

  const updateTimer = () => {
    if (!timerEl) return;
    if (phase !== "test") {
      timerEl.setAttribute("hidden", "");
      return;
    }
    timerEl.removeAttribute("hidden");
    const minutes = Math.floor(remainingSeconds / 60);
    const seconds = remainingSeconds % 60;
    timerEl.textContent = `Time left ${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
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

  const loadQuestion = async () => {
    const params = new URLSearchParams({
      section_index: String(sectionIndex),
      phase,
      question_index: String(questionIndex),
    });
    const response = await fetch(`${player.dataset.questionUrl}?${params.toString()}`, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load the next question.");
    }
    return payload;
  };

  const renderQuestion = async () => {
    if (questionIndex >= getCurrentQuestionCount()) {
      finishPhase();
      return;
    }

    try {
      activeQuestion = await loadQuestion();
      hideFeedback();
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
              if (isCorrect) {
                showFeedback("Correct.", "correct");
                window.setTimeout(() => {
                  hideFeedback();
                  questionIndex += 1;
                  renderQuestion();
                }, 900);
              } else {
                showFeedback("Wrong. Try again.", "wrong");
              }
              return;
            }

            const sectionId = getCurrentSection()?.section_id;
            const entry = collectedTestAnswers.find((row) => row.section_id === sectionId);
            const answerRow = { question_index: questionIndex, selected_option: selected };
            if (entry) {
              const existingIndex = entry.answers.findIndex((row) => row.question_index === questionIndex);
              if (existingIndex >= 0) {
                entry.answers[existingIndex] = answerRow;
              } else {
                entry.answers.push(answerRow);
              }
            } else if (sectionId) {
              collectedTestAnswers.push({ section_id: sectionId, answers: [answerRow] });
            }

            questionIndex += 1;
            renderQuestion();
          });
          optionsEl.appendChild(button);
        });
      }
      showStage(contextStage);
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
    showStage(introStage);
  };

  const renderFullscreenStage = () => {
    stopTimer();
    hideFeedback();
    updateTimer();
    showStage(fullscreenStage);
  };

  const finishPhase = () => {
    stopTimer();
    const section = getCurrentSection();
    if (!section) {
      showStage(completeStage);
      return;
    }

    if (phase === "practice") {
      phase = "test-intro";
      updateEndTestButton();
      if (sectionCompleteLabelEl) sectionCompleteLabelEl.textContent = "Practice complete";
      if (sectionCompleteTitleEl) sectionCompleteTitleEl.textContent = `${section.title} practice complete`;
      if (sectionCompleteCopyEl) sectionCompleteCopyEl.textContent = "Next, start the timed test for this section.";
      if (nextPhaseButton) nextPhaseButton.textContent = "Start timed test";
      showStage(sectionCompleteStage);
      return;
    }

    sectionIndex += 1;
    if (sectionIndex >= sections.length) {
      submitFullTest();
      return;
    }

    phase = "intro";
    if (sectionCompleteLabelEl) sectionCompleteLabelEl.textContent = "Section complete";
    if (sectionCompleteTitleEl) sectionCompleteTitleEl.textContent = `${section.title} test complete`;
    if (sectionCompleteCopyEl) sectionCompleteCopyEl.textContent = "Move on to the next section instructions.";
    if (nextPhaseButton) nextPhaseButton.textContent = "Next section";
    showStage(sectionCompleteStage);
  };

  startButton?.addEventListener("click", async () => {
    const enteredFullscreen = await requestFullscreenFor(player);
    if (!enteredFullscreen) {
      showFeedback("Fullscreen is required to start the full test.", "wrong");
      return;
    }
    hideFeedback();
    questionIndex = 0;
    phase = "practice";
    updateEndTestButton();
    updateTimer();
    renderQuestion();
  });

  fullscreenStartButton?.addEventListener("click", async () => {
    const enteredFullscreen = await requestFullscreenFor(player);
    if (!enteredFullscreen) {
      showFeedback("Fullscreen is required to start timed test mode.", "wrong");
      return;
    }
    hideFeedback();
    questionIndex = 0;
    phase = "test";
    updateEndTestButton();
    startTimer();
    renderQuestion();
  });

  nextPhaseButton?.addEventListener("click", () => {
    if (phase === "test-intro") {
      if (document.fullscreenElement) {
        questionIndex = 0;
        phase = "test";
        updateEndTestButton();
        startTimer();
        renderQuestion();
        return;
      }
      renderFullscreenStage();
      return;
    }
    updateEndTestButton();
    renderIntro();
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
      if (completeSummaryEl) {
        completeSummaryEl.textContent = error.message || "There was a problem submitting the test.";
      }
      isSubmitting = false;
    }

    showStage(completeStage);
  }

  endTestButton?.addEventListener("click", () => {
    if (!confirm("End the test now? Your score so far will be saved.")) return;
    submitFullTest();
  });

  window.addEventListener("beforeunload", () => {
    if (isSubmitting || !player.dataset.submitUrl || phase === "complete") return;
    fetch(player.dataset.submitUrl, {
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
