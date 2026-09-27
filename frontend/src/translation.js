export default function translationPlugin(app) {
  app.config.globalProperties.__ = translate
  window.__ = translate

  function translate(message, ...args) {
    let translated = window.translated_messages?.[message] || message
    if (args.length) {
      return translated.replace(/{(\d+)}/g, (match, number) =>
        typeof args[number] !== 'undefined' ? args[number] : match,
      )
    }
    return translated
  }
}
