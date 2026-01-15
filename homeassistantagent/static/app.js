import "https://esm.sh/@vercel/ai/ui";

const chatElement = document.getElementById("chat");

if (chatElement) {
  chatElement.setAttribute("api", "./api/chat");

  fetch("./api/configure")
    .then((response) => (response.ok ? response.json() : null))
    .then((config) => {
      if (config) {
        chatElement.config = config;
      }
    })
    .catch(() => {
      // Allow the UI to load even if config fetch fails.
    });
}
