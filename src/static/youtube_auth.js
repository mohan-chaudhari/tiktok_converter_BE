document.addEventListener("DOMContentLoaded", () => {
  const authButton = document.getElementById("authButton");
  authButton.addEventListener("click", startYouTubeAuth);

  // Handle callback if we're on the callback page
  if (window.location.pathname === "/youtube/callback") {
    handleCallback();
  }
});

async function startYouTubeAuth() {
  const token = document.getElementById("tokenInput").value.trim();
  const status = document.getElementById("status");
  const result = document.getElementById("result");

  if (!token) {
    status.textContent = "Please enter a login token.";
    return;
  }

  status.textContent = "Initiating YouTube authorization...";
  result.textContent = "";
  console.log("Token used:", token);

  try {
    // Use the token as a query parameter to avoid CORS issues with Google OAuth
    const authHeader = token.startsWith("Bearer ") ? token : `Bearer ${token}`;

    // Redirect directly to our server's auth endpoint with the token
    // This avoids CORS issues by letting the server handle the redirect to Google
    status.textContent = "Redirecting to YouTube authorization...";
      const baseUrl = window.location.origin;
    window.location.href = `${baseUrl}/youtube/auth?token=${encodeURIComponent(
      authHeader
    )}`;
  } catch (error) {
    console.error("Error:", error);
    status.textContent = "Request failed:";
    result.textContent = JSON.stringify(
      {
        error: error.name,
        message: error.message,
        cause: error.cause || "Unknown",
      },
      null,
      2
    );
  }
}

// Handle callback
function handleCallback() {
  const status = document.getElementById("status");
  const result = document.getElementById("result");

  status.textContent = "Processing YouTube Authorization...";

  // Extract any error params
  const urlParams = new URLSearchParams(window.location.search);
  const error = urlParams.get("error");

  if (error) {
    status.textContent = "Authorization Error";
    result.textContent = `Error: ${error}\nDescription: ${
      urlParams.get("error_description") || "No details provided"
    }`;
    return;
  }

  // Show some initial feedback
  status.textContent = "YouTube Authorization Complete!";
  result.textContent = "Processing authorization data...";

  // The server should handle the rest automatically via the callback route
  // Optionally, you could fetch the result of the callback processing:
  fetch(window.location.href, {
    credentials: "include",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      status.textContent = "YouTube Authorization Successful!";
      result.textContent = JSON.stringify(data, null, 2);
    })
    .catch((error) => {
      status.textContent = "Error Processing Authorization";
      result.textContent = `Error: ${error.message}`;
    });
}
