(() => {
  const form = document.querySelector("[data-location-lookup-url]");
  if (!form) return;

  const endpoint = form.dataset.locationLookupUrl;
  const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const cache = new Map();
  let requestCount = 0;
  const maximumRequests = 12;

  document.querySelectorAll("[data-location-input]").forEach((input) => {
    const hidden = document.getElementById(input.dataset.locationHidden);
    const airports = document.getElementById(input.dataset.locationAirports);
    const options = document.getElementById(input.dataset.locationOptions);
    const status = document.getElementById(input.dataset.locationStatus);
    let debounceTimer;
    let controller;
    let activeIndex = -1;
    let currentSuggestions = [];

    const close = () => {
      options.hidden = true;
      options.replaceChildren();
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
      activeIndex = -1;
    };

    const setActive = (nextIndex) => {
      const choices = [...options.querySelectorAll("[role=option]")];
      if (!choices.length) return;
      activeIndex = (nextIndex + choices.length) % choices.length;
      choices.forEach((choice, index) => {
        const selected = index === activeIndex;
        choice.setAttribute("aria-selected", String(selected));
        if (selected) {
          input.setAttribute("aria-activedescendant", choice.id);
          choice.scrollIntoView({ block: "nearest" });
        }
      });
    };

    const choose = (suggestion) => {
      input.value = suggestion.label;
      hidden.value = suggestion.value;
      airports.value = suggestion.airports;
      status.textContent = `Selected ${suggestion.label}.`;
      close();
    };

    const render = (suggestions) => {
      currentSuggestions = suggestions;
      options.replaceChildren();
      suggestions.forEach((suggestion, index) => {
        const choice = document.createElement("button");
        choice.type = "button";
        choice.className = "location-option";
        choice.tabIndex = -1;
        choice.id = `${options.id}-option-${index}`;
        choice.setAttribute("role", "option");
        choice.setAttribute("aria-selected", "false");

        const label = document.createElement("strong");
        label.textContent = suggestion.label;
        const detail = document.createElement("span");
        detail.textContent = suggestion.detail;
        choice.append(label, detail);
        choice.addEventListener("mousedown", (event) => event.preventDefault());
        choice.addEventListener("click", () => choose(suggestion));
        options.append(choice);
      });

      if (suggestions.length) {
        options.hidden = false;
        input.setAttribute("aria-expanded", "true");
        status.textContent = `${suggestions.length} location options available.`;
      } else {
        close();
        status.textContent = "No matching cities or airports.";
      }
    };

    const lookup = async () => {
      const query = input.value.trim();
      if (query.length < 2) {
        close();
        return;
      }
      const cacheKey = query.toLocaleLowerCase();
      if (cache.has(cacheKey)) {
        render(cache.get(cacheKey));
        return;
      }
      if (requestCount >= maximumRequests) {
        close();
        status.textContent =
          "Location lookup limit reached. Enter a 3-letter airport code.";
        return;
      }

      controller?.abort();
      controller = new AbortController();
      requestCount += 1;
      status.textContent = "Looking up cities and airports.";
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": csrfToken,
          },
          body: new URLSearchParams({ q: query }),
          signal: controller.signal,
        });
        if (!response.ok) throw new Error("Location lookup failed.");
        const payload = await response.json();
        const suggestions = Array.isArray(payload.suggestions)
          ? payload.suggestions
          : [];
        cache.set(cacheKey, suggestions);
        render(suggestions);
      } catch (error) {
        if (error.name === "AbortError") return;
        close();
        status.textContent =
          "Location lookup is unavailable. Enter a 3-letter airport code.";
      }
    };

    input.addEventListener("input", () => {
      controller?.abort();
      controller = undefined;
      hidden.value = "";
      airports.value = "";
      close();
      status.textContent = "";
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(lookup, 550);
    });

    input.addEventListener("keydown", (event) => {
      if (options.hidden) return;
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActive(activeIndex + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActive(activeIndex - 1);
      } else if (event.key === "Enter" && activeIndex >= 0) {
        event.preventDefault();
        choose(currentSuggestions[activeIndex]);
      } else if (event.key === "Escape") {
        event.preventDefault();
        close();
      }
    });

    input.addEventListener("blur", () => {
      window.setTimeout(close, 100);
    });
  });
})();
