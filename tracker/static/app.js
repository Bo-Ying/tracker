(function () {
  var LANG_KEY = "tracker-lang";
  var TAB_KEY = "tracker-tab";

  function store(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) {}
  }

  function recall(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  // Language toggle
  function setLang(lang) {
    var root = document.documentElement;
    root.setAttribute("data-lang", lang);
    root.lang = lang === "zh" ? "zh-CN" : "en";
    store(LANG_KEY, lang);
    var buttons = document.querySelectorAll("[data-set-lang]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed", String(buttons[i].getAttribute("data-set-lang") === lang));
    }
  }

  // Column tabs
  var tabs = document.querySelectorAll("[data-tab]");
  var panels = document.querySelectorAll("[data-panel]");

  function hasTab(key) {
    for (var i = 0; i < tabs.length; i++) if (tabs[i].getAttribute("data-tab") === key) return true;
    return false;
  }

  function setTab(key, updateHash) {
    if (!tabs.length) return;
    if (!hasTab(key)) key = tabs[0].getAttribute("data-tab");
    for (var i = 0; i < tabs.length; i++) {
      var active = tabs[i].getAttribute("data-tab") === key;
      tabs[i].classList.toggle("is-active", active);
      tabs[i].setAttribute("aria-selected", String(active));
    }
    for (var j = 0; j < panels.length; j++) {
      panels[j].classList.toggle("is-active", panels[j].getAttribute("data-panel") === key);
    }
    store(TAB_KEY, key);
    if (updateHash && history.replaceState) history.replaceState(null, "", "#" + key);
  }

  document.addEventListener("click", function (event) {
    var target = event.target.closest ? event.target : null;
    if (!target) return;
    var langButton = target.closest("[data-set-lang]");
    if (langButton) {
      setLang(langButton.getAttribute("data-set-lang"));
      return;
    }
    var tab = target.closest("[data-tab]");
    if (tab) {
      event.preventDefault();
      setTab(tab.getAttribute("data-tab"), true);
    }
  });

  window.addEventListener("hashchange", function () {
    setTab(location.hash.slice(1), false);
  });

  setLang(document.documentElement.getAttribute("data-lang") === "zh" ? "zh" : "en");
  setTab(location.hash.slice(1) || recall(TAB_KEY) || "", false);
})();
