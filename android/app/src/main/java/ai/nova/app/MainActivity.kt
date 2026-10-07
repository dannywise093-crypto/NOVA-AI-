package ai.nova.app

import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private val prefs by lazy { getSharedPreferences("nova", MODE_PRIVATE) }
    private lateinit var endpoint: EditText
    private lateinit var status: TextView
    private lateinit var email: EditText
    private lateinit var password: EditText
    private lateinit var message: EditText
    private lateinit var output: TextView
    private lateinit var authButton: Button
    private lateinit var sendButton: Button
    private val history = mutableListOf<JSONObject>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (prefs.getString("token", null) != null) showAuthenticated()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(28, 28, 28, 24)
        }
        val title = TextView(this).apply { text = "NOVA AI"; textSize = 30f }
        status = TextView(this).apply { text = "Not signed in"; textSize = 14f }
        endpoint = EditText(this).apply {
            hint = "API base URL"
            setText(prefs.getString("api", "http://10.0.2.2:8000"))
            singleLine = true
        }
        email = EditText(this).apply {
            hint = "Email"
            inputType = 33
            setText(prefs.getString("email", ""))
            singleLine = true
        }
        password = EditText(this).apply {
            hint = "Password (8+ characters)"
            inputType = 129
            singleLine = true
        }
        authButton = Button(this).apply { text = "Sign In / Create Account" }
        message = EditText(this).apply { hint = "Message NOVA"; minLines = 2; isEnabled = false }
        sendButton = Button(this).apply { text = "Send"; isEnabled = false }
        output = TextView(this).apply { text = "Connect to your NOVA backend to begin."; textSize = 16f }

        root.addView(title)
        root.addView(status)
        root.addView(endpoint)
        root.addView(email)
        root.addView(password)
        root.addView(authButton)
        root.addView(message)
        root.addView(sendButton)
        root.addView(output)
        setContentView(root)

        authButton.setOnClickListener { authenticate() }
        sendButton.setOnClickListener { sendMessage() }
    }

    private fun baseUrl(): String = endpoint.text.toString().trim().trimEnd('/')

    private fun authenticate() {
        val base = baseUrl()
        val userEmail = email.text.toString().trim()
        val userPassword = password.text.toString()
        if (base.isBlank() || userEmail.isBlank() || userPassword.length < 8) {
            status.text = "Enter API URL, email, and an 8+ character password."
            return
        }
        prefs.edit().putString("api", base).putString("email", userEmail).apply()
        setBusy(true)
        status.text = "Signing in..."
        thread {
            val result = requestJson("POST", "$base/api/auth/login",
                JSONObject().put("email", userEmail).put("password", userPassword))
            if (result.code == 401 || result.code == 404) {
                val registration = requestJson("POST", "$base/api/auth/register",
                    JSONObject().put("email", userEmail).put("password", userPassword))
                if (registration.code in 200..299) {
                    handleLogin(requestJson("POST", "$base/api/auth/login",
                        JSONObject().put("email", userEmail).put("password", userPassword)))
                } else {
                    runOnUiThread { showError("Account creation failed: " + registration.body) }
                }
            } else {
                handleLogin(result)
            }
        }
    }

    private fun handleLogin(result: HttpResult) {
        if (result.code !in 200..299) {
            runOnUiThread { showError("Authentication failed: " + result.body) }
            return
        }
        try {
            val token = JSONObject(result.body).getString("access_token")
            prefs.edit().putString("token", token).apply()
            runOnUiThread { showAuthenticated() }
        } catch (e: Exception) {
            runOnUiThread { showError("Invalid login response: " + e.message) }
        }
    }

    private fun showAuthenticated() {
        status.text = "Signed in • NOVA ready"
        password.visibility = View.GONE
        authButton.text = "Signed In"
        authButton.isEnabled = false
        message.isEnabled = true
        sendButton.isEnabled = true
        output.text = "Ask NOVA anything."
    }

    private fun sendMessage() {
        val text = message.text.toString().trim()
        if (text.isBlank()) return
        val token = prefs.getString("token", null)
        if (token == null) {
            status.text = "Please sign in first."
            return
        }

        val historyArray = JSONArray()
        history.forEach { historyArray.put(it) }
        val payload = JSONObject().put("message", text).put("history", historyArray)

        message.text.clear()
        output.text = "NOVA is thinking..."
        sendButton.isEnabled = false

        thread {
            val result = requestJson("POST", baseUrl() + "/api/chat", payload, "Bearer " + token)
            if (result.code in 200..299) {
                try {
                    val json = JSONObject(result.body)
                    val answer = json.optString("content", "No response.")
                    history.add(JSONObject().put("role", "user").put("content", text))
                    history.add(JSONObject().put("role", "assistant").put("content", answer))
                    runOnUiThread {
                        output.text = answer
                        sendButton.isEnabled = true
                    }
                } catch (e: Exception) {
                    runOnUiThread { showError("Invalid NOVA response: " + e.message) }
                }
            } else if (result.code == 401) {
                prefs.edit().remove("token").apply()
                runOnUiThread {
                    status.text = "Session expired. Sign in again."
                    sendButton.isEnabled = true
                }
            } else {
                runOnUiThread { showError("Chat failed (" + result.code + "): " + result.body) }
            }
        }
    }

    private fun requestJson(
        method: String,
        url: String,
        body: JSONObject? = null,
        authorization: String? = null
    ): HttpResult {
        return try {
            val connection = URL(url).openConnection() as HttpURLConnection
            connection.connectTimeout = 10_000
            connection.readTimeout = 60_000
            connection.requestMethod = method
            connection.setRequestProperty("Accept", "application/json")
            if (authorization != null) connection.setRequestProperty("Authorization", authorization)
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code >= 400) connection.errorStream else connection.inputStream
            val response = stream?.bufferedReader()?.use { it.readText() } ?: ""
            connection.disconnect()
            HttpResult(code, response)
        } catch (e: Exception) {
            HttpResult(-1, "ERROR: " + e.message)
        }
    }

    private fun showError(messageText: String) {
        status.text = messageText
        output.text = messageText
        sendButton.isEnabled = prefs.getString("token", null) != null
        setBusy(false)
    }

    private fun setBusy(busy: Boolean) {
        authButton.isEnabled = !busy
        sendButton.isEnabled = !busy && prefs.getString("token", null) != null
    }

    data class HttpResult(val code: Int, val body: String)
}
