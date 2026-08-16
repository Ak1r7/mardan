(() => {
  const body = document.body;
  const menuButton = document.querySelector<HTMLButtonElement>('.menu-toggle');
  const nav = document.querySelector<HTMLElement>('.site-nav');
  const navLinks = Array.from(document.querySelectorAll<HTMLAnchorElement>('.site-nav a'));
  const requestModal = document.querySelector<HTMLElement>('#request-modal');
  const gallery = document.querySelector<HTMLElement>('#gallery-modal');
  const galleryImage = gallery?.querySelector<HTMLImageElement>('img') ?? null;
  const modalTitle = document.querySelector<HTMLElement>('#modal-title');
  let previouslyFocused: HTMLElement | null = null;

  const setMenuState = (open: boolean): void => {
    nav?.classList.toggle('is-open', open);
    menuButton?.setAttribute('aria-expanded', String(open));
    menuButton?.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
  };

  menuButton?.addEventListener('click', () => {
    setMenuState(!nav?.classList.contains('is-open'));
  });
  navLinks.forEach((link) => link.addEventListener('click', () => setMenuState(false)));

  const sections = Array.from(document.querySelectorAll<HTMLElement>('main section[id]'));
  const updateActiveNav = (): void => {
    const offset = window.scrollY + 130;
    let active = 'home';
    sections.forEach((section) => {
      if (section.offsetTop <= offset) active = section.id;
    });
    navLinks.forEach((link) => {
      const isActive = link.getAttribute('href') === `#${active}`;
      link.classList.toggle('active', isActive);
      if (isActive) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  };
  document.addEventListener('scroll', updateActiveNav, { passive: true });
  updateActiveNav();

  const observer = 'IntersectionObserver' in window
    ? new IntersectionObserver((entries, instance) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            instance.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 })
    : null;
  document.querySelectorAll<HTMLElement>('.reveal').forEach((item) => {
    if (observer) observer.observe(item);
    else item.classList.add('is-visible');
  });

  const filterButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('[data-filter]'));
  const cards = Array.from(document.querySelectorAll<HTMLElement>('.project-card'));
  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const filter = button.dataset.filter ?? 'all';
      filterButtons.forEach((item) => {
        const selected = item === button;
        item.classList.toggle('active', selected);
        item.setAttribute('aria-pressed', String(selected));
      });
      cards.forEach((card) => {
        const hidden = filter !== 'all' && card.dataset.category !== filter;
        card.classList.toggle('is-hidden', hidden);
        card.toggleAttribute('hidden', hidden);
      });
    });
  });

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll<HTMLDetailsElement>('.faq-list details').forEach((details) => {
    const summary = details.querySelector<HTMLElement>('summary');
    const answer = details.querySelector<HTMLElement>('.faq-answer');
    if (!summary || !answer || reduceMotion) return;
    if (details.open) answer.style.height = 'auto';

    summary.addEventListener('click', (event) => {
      event.preventDefault();
      if (details.dataset.animating === 'true') return;
      details.dataset.animating = 'true';

      if (details.open) {
        answer.style.height = `${answer.scrollHeight}px`;
        requestAnimationFrame(() => {
          answer.style.height = '0px';
          answer.style.opacity = '0';
        });
        const finishClose = (transitionEvent: TransitionEvent): void => {
          if (transitionEvent.propertyName !== 'height') return;
          answer.removeEventListener('transitionend', finishClose);
          details.open = false;
          answer.style.removeProperty('height');
          answer.style.removeProperty('opacity');
          delete details.dataset.animating;
        };
        answer.addEventListener('transitionend', finishClose);
      } else {
        details.open = true;
        answer.style.height = '0px';
        answer.style.opacity = '0';
        requestAnimationFrame(() => {
          answer.style.height = `${answer.scrollHeight}px`;
          answer.style.opacity = '1';
        });
        const finishOpen = (transitionEvent: TransitionEvent): void => {
          if (transitionEvent.propertyName !== 'height') return;
          answer.removeEventListener('transitionend', finishOpen);
          answer.style.height = 'auto';
          answer.style.removeProperty('opacity');
          delete details.dataset.animating;
        };
        answer.addEventListener('transitionend', finishOpen);
      }
    });
  });

  const focusableSelector = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
  const trapFocus = (container: HTMLElement, event: KeyboardEvent): void => {
    if (event.key !== 'Tab') return;
    const focusable = Array.from(container.querySelectorAll<HTMLElement>(focusableSelector)).filter((element) => element.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const openRequestModal = (title?: string): void => {
    if (!requestModal) return;
    previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    requestModal.hidden = false;
    if (modalTitle) modalTitle.textContent = title || 'Получить предварительную смету';
    requestModal.classList.add('is-open');
    requestModal.setAttribute('aria-hidden', 'false');
    body.classList.add('modal-open');
    requestModal.querySelector<HTMLElement>('input:not([type="hidden"]), textarea, button')?.focus();
  };

  const closeRequestModal = (): void => {
    if (!requestModal?.classList.contains('is-open')) return;
    requestModal.classList.remove('is-open');
    requestModal.setAttribute('aria-hidden', 'true');
    requestModal.hidden = true;
    body.classList.remove('modal-open');
    previouslyFocused?.focus();
  };

  document.querySelectorAll<HTMLElement>('.js-open-modal').forEach((button) => {
    button.addEventListener('click', () => openRequestModal(button.dataset.modalTitle));
  });
  document.querySelectorAll<HTMLElement>('[data-close-modal]').forEach((button) => button.addEventListener('click', closeRequestModal));

  document.querySelectorAll<HTMLButtonElement>('.js-open-gallery').forEach((button) => {
    button.addEventListener('click', () => {
      if (!gallery || !galleryImage) return;
      previouslyFocused = button;
      gallery.hidden = false;
      galleryImage.src = button.dataset.image ?? '';
      galleryImage.alt = button.dataset.alt ?? 'Увеличенная фотография проекта';
      gallery.classList.add('is-open');
      gallery.setAttribute('aria-hidden', 'false');
      body.classList.add('modal-open');
      gallery.querySelector<HTMLButtonElement>('[data-close-gallery]')?.focus();
    });
  });

  const closeGallery = (): void => {
    if (!gallery?.classList.contains('is-open')) return;
    gallery.classList.remove('is-open');
    gallery.setAttribute('aria-hidden', 'true');
    gallery.hidden = true;
    body.classList.remove('modal-open');
    previouslyFocused?.focus();
  };
  document.querySelectorAll<HTMLElement>('[data-close-gallery]').forEach((button) => button.addEventListener('click', closeGallery));
  gallery?.addEventListener('click', (event) => {
    if (event.target === gallery) closeGallery();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setMenuState(false);
      closeRequestModal();
      closeGallery();
      return;
    }
    if (requestModal?.classList.contains('is-open')) trapFocus(requestModal, event);
    else if (gallery?.classList.contains('is-open')) trapFocus(gallery, event);
  });

  const phoneMask = (input: HTMLInputElement): void => {
    const digits = input.value.replace(/\D/g, '').slice(0, 11);
    if (!digits) {
      input.value = '';
      return;
    }
    const local = digits.startsWith('7') || digits.startsWith('8') ? digits.slice(1) : digits;
    let formatted = '+7';
    if (local.length) formatted += ` (${local.slice(0, 3)}`;
    if (local.length >= 3) formatted += ')';
    if (local.length > 3) formatted += ` ${local.slice(3, 6)}`;
    if (local.length > 6) formatted += `-${local.slice(6, 8)}`;
    if (local.length > 8) formatted += `-${local.slice(8, 10)}`;
    input.value = formatted;
  };
  document.querySelectorAll<HTMLInputElement>('input[type="tel"]').forEach((input) => {
    input.addEventListener('input', () => phoneMask(input));
  });

  const namedField = <T extends HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(form: HTMLFormElement, name: string): T | null => {
    const item = form.elements.namedItem(name);
    return item instanceof HTMLInputElement || item instanceof HTMLTextAreaElement || item instanceof HTMLSelectElement ? item as T : null;
  };

  const clearFieldError = (field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null): void => {
    if (!field) return;
    field.removeAttribute('aria-invalid');
    const error = field.id ? document.querySelector<HTMLElement>(`#${CSS.escape(field.id)}-error`) : null;
    if (error) error.textContent = '';
  };

  const setFieldError = (field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null, message: string): void => {
    if (!field) return;
    field.setAttribute('aria-invalid', 'true');
    const error = field.id ? document.querySelector<HTMLElement>(`#${CSS.escape(field.id)}-error`) : null;
    if (error) {
      error.textContent = message;
      const describedBy = new Set((field.getAttribute('aria-describedby') ?? '').split(/\s+/).filter(Boolean));
      describedBy.add(error.id);
      field.setAttribute('aria-describedby', Array.from(describedBy).join(' '));
    }
  };

  const validateForm = (form: HTMLFormElement): string[] => {
    const errors: string[] = [];
    const name = namedField<HTMLInputElement>(form, 'name');
    const phone = namedField<HTMLInputElement>(form, 'phone');
    const message = namedField<HTMLTextAreaElement>(form, 'message');
    const consent = namedField<HTMLInputElement>(form, 'consent');
    const website = namedField<HTMLInputElement>(form, 'website');
    [name, phone, message, consent].forEach(clearFieldError);

    const nameValue = name?.value.trim() ?? '';
    const phoneDigits = phone?.value.replace(/\D/g, '') ?? '';
    if (website?.value.trim()) errors.push('Форма отправлена некорректно.');
    if (nameValue.length < 2 || nameValue.length > 80) {
      const text = 'Укажите имя длиной от 2 до 80 символов.';
      errors.push(text);
      setFieldError(name, text);
    }
    if (phoneDigits.length < 10 || phoneDigits.length > 11) {
      const text = 'Укажите корректный номер телефона.';
      errors.push(text);
      setFieldError(phone, text);
    }
    if ((message?.value.length ?? 0) > 800) {
      const text = 'Комментарий должен быть не длиннее 800 символов.';
      errors.push(text);
      setFieldError(message, text);
    }
    if (consent && !consent.checked) {
      const text = 'Нужно согласие на обработку персональных данных.';
      errors.push(text);
      setFieldError(consent, text);
    }
    return errors;
  };

  const submitForm = async (form: HTMLFormElement): Promise<void> => {
    const status = form.querySelector<HTMLElement>('.form-message');
    const submitButton = form.querySelector<HTMLButtonElement>('button[type="submit"]');
    if (!status || !submitButton) return;
    status.textContent = '';
    status.className = 'form-message';
    const errors = validateForm(form);
    if (errors.length) {
      status.textContent = errors[0] ?? 'Проверьте заполнение формы.';
      status.classList.add('error');
      form.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
      return;
    }
    if (window.location.protocol === 'file:') {
      status.textContent = 'Автономная HTML-версия предназначена для просмотра. Для отправки заявки откройте основную версию на PHP-хостинге или позвоните по телефону.';
      status.classList.add('error');
      return;
    }

    const originalLabel = submitButton.textContent ?? 'Отправить';
    submitButton.disabled = true;
    submitButton.textContent = 'Отправка…';
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(form),
        credentials: 'same-origin',
      });
      const contentType = response.headers.get('content-type') ?? '';
      const data = contentType.includes('application/json') ? await response.json() as { ok?: boolean; message?: string } : null;
      if (!response.ok || !data?.ok) throw new Error(data?.message || 'Не удалось отправить форму.');
      status.textContent = data.message || 'Заявка отправлена.';
      status.classList.add('success');
      form.reset();
      const startedAt = namedField<HTMLInputElement>(form, 'form_started_at');
      if (startedAt) startedAt.value = String(Date.now());
      form.dispatchEvent(new CustomEvent('site:form-success'));
    } catch (error: unknown) {
      status.textContent = error instanceof Error ? error.message : 'Произошла ошибка. Попробуйте позже или свяжитесь по телефону.';
      status.classList.add('error');
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = originalLabel;
    }
  };


  const heroQuiz = document.querySelector<HTMLFormElement>('[data-hero-quiz]');
  if (heroQuiz) {
    const quizSteps = Array.from(heroQuiz.querySelectorAll<HTMLElement>('[data-quiz-step]'));
    const quizSuccess = heroQuiz.querySelector<HTMLElement>('[data-quiz-success]');
    const quizTitle = heroQuiz.querySelector<HTMLElement>('#hero-quiz-title');
    const quizError = heroQuiz.querySelector<HTMLElement>('[data-quiz-error]');
    const quizProgress = heroQuiz.querySelector<HTMLElement>('[data-quiz-progress]');
    const quizProgressFill = quizProgress?.querySelector<HTMLElement>('span') ?? null;
    const quizProgressLabel = heroQuiz.querySelector<HTMLElement>('[data-quiz-progress-label]');
    const quizBack = heroQuiz.querySelector<HTMLButtonElement>('[data-quiz-back]');
    const quizNext = heroQuiz.querySelector<HTMLButtonElement>('[data-quiz-next]');
    const quizSubmit = heroQuiz.querySelector<HTMLButtonElement>('[data-quiz-submit]');
    const quizFooter = heroQuiz.querySelector<HTMLElement>('[data-quiz-footer]');
    const quizMessage = heroQuiz.querySelector<HTMLTextAreaElement>('[data-quiz-message]');
    const quizSummary = heroQuiz.querySelector<HTMLElement>('[data-quiz-summary]');
    const quizResetButtons = Array.from(heroQuiz.querySelectorAll<HTMLButtonElement>('[data-quiz-reset], [data-quiz-restart]'));
    const progressValues = [0, 17, 33, 67, 95];
    let currentQuizStep = 0;

    const selectedLabels = (name: string): string[] => {
      return Array.from(heroQuiz.querySelectorAll<HTMLInputElement>(`input[name="${name}"]:checked`))
        .map((input) => input.dataset.label || input.value)
        .filter(Boolean);
    };

    const createQuizMessage = (): string => {
      const rooms = selectedLabels('rooms[]').join(', ');
      const repair = selectedLabels('repair')[0] ?? 'Не указано';
      const timing = selectedLabels('timing')[0] ?? 'Не указано';
      const budget = selectedLabels('budget')[0] ?? 'Не указано';
      return [
        'Квиз с главной страницы.',
        `Комнаты: ${rooms || 'Не указано'}.`,
        `Тип ремонта: ${repair}.`,
        `Начало работ: ${timing}.`,
        `Бюджет: ${budget}.`,
      ].join('\n');
    };

    const updateQuizSummary = (): void => {
      if (!quizSummary) return;
      const rooms = selectedLabels('rooms[]');
      const repair = selectedLabels('repair')[0] ?? '—';
      const budget = selectedLabels('budget')[0] ?? '—';
      const roomText = rooms.length > 2 ? `${rooms.slice(0, 2).join(', ')} и ещё ${rooms.length - 2}` : rooms.join(', ');
      quizSummary.textContent = `${roomText || 'Помещения не выбраны'} · ${repair} · ${budget}`;
      if (quizMessage) quizMessage.value = createQuizMessage();
    };

    const validateQuizStep = (stepIndex: number): boolean => {
      const requirements: Record<number, { name: string; message: string }> = {
        0: { name: 'rooms[]', message: 'Выберите хотя бы одно помещение.' },
        1: { name: 'repair', message: 'Выберите подходящий тип ремонта.' },
        2: { name: 'timing', message: 'Укажите, когда хотите начать ремонт.' },
        3: { name: 'budget', message: 'Выберите примерный бюджет.' },
      };
      const requirement = requirements[stepIndex];
      if (!requirement) return true;
      const valid = selectedLabels(requirement.name).length > 0;
      if (!valid && quizError) quizError.textContent = requirement.message;
      return valid;
    };

    const setQuizStep = (stepIndex: number, focus = false): void => {
      currentQuizStep = Math.max(0, Math.min(stepIndex, quizSteps.length - 1));
      quizSuccess?.setAttribute('hidden', '');
      quizFooter?.removeAttribute('hidden');
      quizSteps.forEach((step, index) => {
        const active = index === currentQuizStep;
        step.toggleAttribute('hidden', !active);
        step.classList.toggle('is-active', active);
      });
      const activeStep = quizSteps[currentQuizStep];
      if (quizTitle) quizTitle.textContent = activeStep?.dataset.title ?? 'Расчёт стоимости ремонта';
      if (quizError) quizError.textContent = '';
      const progressValue = progressValues[currentQuizStep] ?? 0;
      quizProgress?.setAttribute('aria-valuenow', String(progressValue));
      if (quizProgressFill) quizProgressFill.style.width = `${progressValue}%`;
      if (quizProgressLabel) quizProgressLabel.textContent = `${progressValue}%`;
      if (quizBack) quizBack.disabled = currentQuizStep === 0;
      const isFinal = currentQuizStep === quizSteps.length - 1;
      quizNext?.toggleAttribute('hidden', isFinal);
      quizSubmit?.toggleAttribute('hidden', !isFinal);
      if (isFinal) updateQuizSummary();
      if (focus) {
        const target = activeStep?.querySelector<HTMLElement>('input, button, [tabindex]');
        target?.focus({ preventScroll: true });
      }
    };

    const resetQuiz = (): void => {
      heroQuiz.reset();
      const startedAt = namedField<HTMLInputElement>(heroQuiz, 'form_started_at');
      if (startedAt) startedAt.value = String(Date.now());
      const status = heroQuiz.querySelector<HTMLElement>('.form-message');
      if (status) {
        status.textContent = '';
        status.className = 'form-message hero-quiz-message';
      }
      setQuizStep(0, false);
    };

    quizNext?.addEventListener('click', () => {
      if (!validateQuizStep(currentQuizStep)) return;
      setQuizStep(currentQuizStep + 1, true);
    });
    quizBack?.addEventListener('click', () => setQuizStep(currentQuizStep - 1, true));
    quizResetButtons.forEach((button) => button.addEventListener('click', resetQuiz));
    heroQuiz.addEventListener('change', () => {
      if (quizError) quizError.textContent = '';
    });
    heroQuiz.addEventListener('submit', (event) => {
      if (currentQuizStep !== quizSteps.length - 1) {
        event.preventDefault();
        if (validateQuizStep(currentQuizStep)) setQuizStep(currentQuizStep + 1, true);
        return;
      }
      updateQuizSummary();
    });
    heroQuiz.addEventListener('site:form-success', () => {
      quizSteps.forEach((step) => step.setAttribute('hidden', ''));
      quizSuccess?.removeAttribute('hidden');
      quizFooter?.setAttribute('hidden', '');
      if (quizTitle) quizTitle.textContent = 'Спасибо! Расчёт уже начат';
      if (quizError) quizError.textContent = '';
      const status = heroQuiz.querySelector<HTMLElement>('.form-message');
      if (status) status.textContent = '';
    });

    setQuizStep(0, false);
  }

  document.querySelectorAll<HTMLFormElement>('.js-contact-form').forEach((form) => {
    const startedAt = namedField<HTMLInputElement>(form, 'form_started_at');
    if (startedAt) startedAt.value = String(Date.now());
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      void submitForm(form);
    });
  });

  const year = document.querySelector<HTMLElement>('#year');
  if (year) year.textContent = String(new Date().getFullYear());
})();
