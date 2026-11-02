(function () {
  var KEY = "tracker-lang";

  function setLang(lang) {
    var root = document.documentElement;
    root.setAttribute("data-lang", lang);
    root.lang = lang === "zh" ? "zh-CN" : "en";
    try {
      localStorage.setItem(KEY, lang);
    } catch (e) {}
    var buttons = document.querySelectorAll("[data-set-lang]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed", String(buttons[i].getAttribute("data-set-lang") === lang));
    }
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-set-lang]");
    if (button) setLang(button.getAttribute("data-set-lang"));
  });

  setLang(document.documentElement.getAttribute("data-lang") === "zh" ? "zh" : "en");
})();
