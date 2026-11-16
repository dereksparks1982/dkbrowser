"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const text = {
    en: {
      title:"DK AI",localeLabel:"Language",subtitle:"Private local AI assistant",
      intro:"Chats stay on your computer and go only to the AI model service on this machine. No account is required.",
      modelLabel:"Installed model",refresh:"Refresh models",inputLabel:"Your message",
      clear:"Clear chat",send:"Send",privacy:"No cloud account • No hidden browsing access • No automatic model downloads",
      placeholder:"Ask a question…",noModels:"No local models found. Install a model in Ollama first.",
      loading:"Looking for local models…",ready:"Ready. Choose a model and ask a question.",
      unavailable:"Local model service unavailable. Start Ollama and install a model.",
      thinking:"The local model is replying…",error:"An error occurred: ",answer:"Assistant: ",
      yourMessage:"You: "
    },
    ru: {
      title:"ДК ИИ",localeLabel:"Язык",subtitle:"Личный помощник с искусственным интеллектом",
      intro:"Переписка остаётся на вашем компьютере и передаётся только местной службе обработки запросов. Учётная запись не требуется.",
      modelLabel:"Установленная модель",refresh:"Обновить список",inputLabel:"Ваше сообщение",
      clear:"Очистить переписку",send:"Отправить",privacy:"Без облачной учётной записи • Без скрытого доступа к сайтам • Без автоматической загрузки моделей",
      placeholder:"Задайте вопрос…",noModels:"Местные модели не найдены. Сначала установите модель.",
      loading:"Поиск установленных моделей…",ready:"Готово. Выберите модель и задайте вопрос.",
      unavailable:"Местная служба недоступна. Запустите её и установите модель.",
      thinking:"Модель отвечает…",error:"Произошла ошибка: ",answer:"Помощник: ",
      yourMessage:"Вы: "
    }
  };
  let language = "en";
  let messages = [];
  let busy = false;

  function tr(key) { return text[language][key]; }
  function setStatus(value) { $("status").textContent = value; }
  function applyLocale() {
    language = $("locale").value === "ru" ? "ru" : "en";
    document.documentElement.lang = language;
    document.title = tr("title");
    for (const key of ["title","localeLabel","subtitle","intro","modelLabel","refresh",
                        "inputLabel","clear","send","privacy"]) $(key).textContent = tr(key);
    $("input").placeholder = tr("placeholder");
    $("locale").setAttribute("aria-label", tr("localeLabel"));
    if (!busy) setStatus($("model").options.length ? tr("ready") : tr("noModels"));
  }
  function display(role, content) {
    const line = document.createElement("div");
    line.className = "message " + role;
    line.textContent = (role === "user" ? tr("yourMessage") : tr("answer")) + content;
    $("chat").append(line);
    $("chat").scrollTop = $("chat").scrollHeight;
  }
  async function loadModels() {
    setStatus(tr("loading"));
    $("refresh").disabled = true;
    try {
      const response = await fetch("/api/models", {cache:"no-store"});
      const data = await response.json();
      if (!response.ok) throw Error(data.error || response.statusText);
      const select = $("model");
      const former = select.value;
      select.replaceChildren();
      for (const model of data.models) {
        const option = document.createElement("option");
        option.value = model;
        option.textContent = model;
        select.add(option);
      }
      if (Array.from(select.options).some(option => option.value === former))
        select.value = former;
      setStatus(select.options.length ? tr("ready") : tr("noModels"));
    } catch (_) {
      $("model").replaceChildren();
      setStatus(tr("unavailable"));
    } finally {
      $("refresh").disabled = false;
    }
  }
  $("locale").addEventListener("change", applyLocale);
  $("refresh").addEventListener("click", loadModels);
  $("clear").addEventListener("click", () => {
    if (busy) return;
    messages = [];
    $("chat").replaceChildren();
    $("input").value = "";
  });
  $("composer").addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = $("input").value.trim();
    const model = $("model").value;
    if (!question || !model || busy) return;
    busy = true;
    $("send").disabled = true;
    $("input").disabled = true;
    $("input").value = "";
    display("user", question);
    messages.push({role:"user",content:question});
    if (messages.length > 29) messages = messages.slice(-29);
    setStatus(tr("thinking"));
    try {
      const response = await fetch("/api/chat", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({model, messages})
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.error || response.statusText);
      display("assistant", data.answer);
      messages.push({role:"assistant",content:data.answer});
      setStatus(tr("ready"));
    } catch (error) {
      // Leave the question in the chat, but discard it from the model history
      // to prevent sending duplicate messages on retry.
      messages.pop();
      setStatus(tr("error") + String(error.message || error));
    } finally {
      busy = false;
      $("send").disabled = false;
      $("input").disabled = false;
      $("input").focus();
    }
  });
  applyLocale();
  loadModels();
})();
