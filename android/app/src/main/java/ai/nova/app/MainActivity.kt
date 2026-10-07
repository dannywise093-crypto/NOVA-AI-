package ai.nova.app

import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.Gravity
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
    private lateinit var email: EditText
    private lateinit var password: EditText
    private lateinit var message: EditText
    private lateinit var status: TextView
    private lateinit var messages: LinearLayout
    private lateinit var sendButton: Button
    private lateinit var authButton: Button
    private lateinit var modelSpinner: Spinner
    private val history = mutableListOf<JSONObject>()
    private var streaming = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        if (prefs.getString("token", null) != null) showChat()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(15, 15, 18))
            setPadding(20, 20, 20, 16)
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val title = TextView(this).apply {
            text = "NOVA"
            textSize = 28f
            setTextColor(Color.WHITE)
        }
        status = TextView(this).apply {
            text = "Offline"
            textSize = 13f
            setTextColor(Color.LTGRAY)
            gravity = Gravity.END
        }
        header.addView(title, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(status)

        endpoint = field("API base URL", prefs.getString("api", "http://10.0.2.2:8000"))
        email = field("Email", prefs.getString("email", ""))
        password = field("Password", "")
        password.inputType = 129
        authButton = Button(this).apply { text = "Sign In / Create Account" }
        modelSpinner = Spinner(this)

        messages = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val scroll = ScrollView(this).apply { addView(messages) }

        message = EditText(this).apply {
            hint = "Message NOVA..."
            minLines = 2
            setTextColor(Color.WHITE)
            setHintTextColor(Color.GRAY)
            setBackgroundColor(Color.rgb(30, 30, 35))
            isEnabled = false
        }
        sendButton = Button(this).apply {
            text = "Send"
            isEnabled = false
        }
        val composer = LinearLayout(this).apply {
            gravity = Gravity.BOTTOM
            addView(message, LinearLayout.LayoutParams(0, -2, 1f))
            addView(sendButton, LinearLayout.LayoutParams(-2, -2))
        }

        root.addView(header)
        root.addView(endpoint)
        root.addView(email)
        root.addView(password)
        root.addView(authButton)
        root.addView(modelSpinner)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(composer)
        setContentView(root)

        authButton.setOnClickListener { authenticate() }
        sendButton.setOnClickListener { sendMessage() }
    }

    private fun field(hintText: String, value: String?): EditText = EditText(this).apply {
        hint = hintText
        setText(value ?: "")
        singleLine = true
        setTextColor(Color.WHITE)
        setHintTextColor(Color.GRAY)
    }

    private fun bubble(text: String, user: Boolean): TextView {
        val view = TextView(this).apply {
            this.text = text
            textSize = 16f
            setTextColor(Color.WHITE)
            setPadding(18, 14, 18, 14)
            setBackgroundColor(if (user) Color.rgb(45, 45, 55) else Color.rgb(28, 42, 36))
        }
        val params = LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, 8, 0, 8) }
        messages.addView(view, params)
        return view
    }

    private fun authenticate() {
        val base = endpoint.text.toString().trim().trimEnd('/')
        val userEmail = email.text.toString().trim()
        val userPassword = password.text.toString()
        if (base.isBlank() || userEmail.isBlank() || userPassword.length < 8) {
            status.text = "Enter URL, email and 8+ character password"
            return
        }
        prefs.edit().putString("api", base).putString("email", userEmail).apply()
        authButton.isEnabled = false
        status.text = "Signing in..."
        thread {
            val login = request("POST", "$base/api/auth/login",
                JSONObject().put("email", userEmail).put("password", userPassword))
            if (login.code == 401 || login.code == 404) {
                val register = request("POST", "$base/api/auth/register",
                    JSONObject().put("email", userEmail).put("password", userPassword))
                if (register.code in 200..299) {
                    finishLogin(request("POST", "$base/api/auth/login",
                        JSONObject().put("email", userEmail).put("password", userPassword)))
                } else runOnUiThread { authError("Account creation failed: " + register.body) }
            } else finishLogin(login)
        }
    }

    private fun finishLogin(result: HttpResult) {
        if (result.code !in 200..299) {
            runOnUiThread { authError("Authentication failed: " + result.body) }
            return
        }
        try {
            val token = JSONObject(result.body).getString("access_token")
            prefs.edit().putString("token", token).apply()
            runOnUiThread { showChat() }
        } catch (_: Exception) {
            runOnUiThread { authError("Invalid login response") }
        }
    }

    private fun showChat() {
        endpoint.visibility = View.GONE
        email.visibility = View.GONE
        password.visibility = View.GONE
        authButton.visibility = View.GONE
        message.isEnabled = true
        sendButton.isEnabled = true
        status.text = "● Ready"
        modelSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, arrayOf("Auto"))
        loadModels()
        if (messages.childCount == 0) bubble("I'm NOVA. Ask me anything.", false)
    }

    private fun loadModels() {
        val base = prefs.getString("api", "")?.trimEnd('/') ?: return
        thread {
            val result = request("GET", "$base/api/models")
            if (result.code in 200..299) {
                try {
                    val a = JSONArray(result.body)
                    val names = mutableListOf("Auto")
                    for (i in 0 until a.length()) {
                        val id = a.getJSONObject(i).optString("id")
                        if (id.isNotBlank()) names.add(id)
                    }
                    runOnUiThread {
                        modelSpinner.adapter = ArrayAdapter(
                            this, android.R.layout.simple_spinner_dropdown_item, names.distinct()
                        )
                    }
                } catch (_: Exception) {}
            }
        }
    }

    private fun sendMessage() {
        val text = message.text.toString().trim()
        val token = prefs.getString("token", null) ?: return
        if (streaming || text.isBlank()) return
        streaming = true

        val historyArray = JSONArray()
        history.forEach { historyArray.put(it) }

        bubble(text, true)
        message.text.clear()
        sendButton.isEnabled = false
        status.text = "Thinking..."

        val assistant = bubble("NOVA is thinking...", false)
        assistant.setTextColor(Color.LTGRAY)
        val answer = StringBuilder()

        val payload = JSONObject()
            .put("goal", text)
            .put("messages", historyArray)
        val selectedModel = modelSpinner.selectedItem?.toString()?.trim()
        if (!selectedModel.isNullOrBlank() && selectedModel != "Auto") {
            payload.put("model", selectedModel)
        }

        thread {
            streamChat(payload, token, assistant, answer, text)
        }
    }

    private fun streamChat(
        payload: JSONObject,
        token: String,
        assistant: TextView,
        answer: StringBuilder,
        userText: String
    ) {
        var connection: HttpURLConnection? = null
        var finalContent: String? = null
        var failed = false
        try {
            val base = prefs.getString("api", "")!!.trimEnd('/')
            connection = URL("$base/api/stream").openConnection() as HttpURLConnection
            connection.connectTimeout = 10_000
            connection.readTimeout = 120_000
            connection.requestMethod = "POST"
            connection.doOutput = true
            connection.setRequestProperty("Accept", "text/event-stream")
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Authorization", "Bearer $token")
            connection.outputStream.use {
                it.write(payload.toString().toByteArray(Charsets.UTF_8))
            }

            val code = connection.responseCode
            if (code == 401) {
                failed = true
                prefs.edit().remove("token").apply()
                runOnUiThread {
                    assistant.text = "Session expired. Please sign in again."
                    status.text = "Session expired"
                    sendButton.isEnabled = false
                }
                return
            }
            if (code !in 200..299) {
                failed = true
                val body = connection.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
                runOnUiThread {
                    assistant.text = "Stream failed: $body"
                    status.text = "Stream error"
                }
                return
            }

            connection.inputStream.bufferedReader().useLines { lines ->
                lines.forEach { line ->
                    if (!line.startsWith("data:")) return@forEach
                    val raw = line.removePrefix("data:").trim()
                    if (raw.isBlank()) return@forEach
                    try {
                        val event = JSONObject(raw)
                        when (event.optString("type")) {
                            "response.delta" -> {
                                val delta = event.optString("delta")
                                if (delta.isNotEmpty()) {
                                    answer.append(delta)
                                    val visible = answer.toString()
                                    runOnUiThread {
                                        assistant.setText(visible)
                                        assistant.setTextColor(Color.WHITE)
                                        status.text = "Generating..."
                                    }
                                }
                            }
                            "model.selected" -> {
                                val model = event.optString("model")
                                if (model.isNotBlank()) runOnUiThread {
                                    status.text = "Using $model"
                                }
                            }
                            "verification" -> {
                                val verified = event.optBoolean("verified", false)
                                runOnUiThread {
                                    status.text = if (verified) "Verified" else "Verifying..."
                                }
                            }
                            "response.final" -> {
                                val content = event.optString("content")
                                if (content.isNotBlank()) finalContent = content
                            }
                            "error" -> {
                                failed = true
                                val error = event.optString("error", "Unknown stream error")
                                runOnUiThread {
                                    assistant.text = error
                                    assistant.setTextColor(Color.rgb(255, 120, 120))
                                    status.text = "Error"
                                }
                            }
                        }
                    } catch (_: Exception) {
                        // Ignore malformed/heartbeat SSE lines.
                    }
                }
            }

            if (finalContent != null && answer.isEmpty()) {
                answer.append(finalContent)
                runOnUiThread { assistant.setText(finalContent) }
            }

            if (!failed) {
                val finalAnswer = answer.toString().ifBlank { finalContent ?: "No response." }
                history.add(JSONObject().put("role", "user").put("content", userText))
                history.add(JSONObject().put("role", "assistant").put("content", finalAnswer))
                runOnUiThread {
                    assistant.setText(finalAnswer)
                    assistant.setTextColor(Color.WHITE)
                    status.text = "● Ready"
                }
            }
        } catch (e: Exception) {
            failed = true
            runOnUiThread {
                assistant.text = "Connection error: " + (e.message ?: "unknown error")
                assistant.setTextColor(Color.rgb(255, 120, 120))
                status.text = "Offline"
            }
        } finally {
            connection?.disconnect()
            runOnUiThread {
                streaming = false
                if (!failed && prefs.getString("token", null) != null) {
                    sendButton.isEnabled = true
                }
            }
        }
    }

    private fun authError(text: String) {
        status.text = text
        authButton.isEnabled = true
    }

    private fun request(
        method: String,
        url: String,
        body: JSONObject? = null,
        auth: String? = null
    ): HttpResult {
        return try {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = 10_000
            c.readTimeout = 60_000
            c.requestMethod = method
            c.setRequestProperty("Accept", "application/json")
            if (auth != null) c.setRequestProperty("Authorization", auth)
            if (body != null) {
                c.doOutput = true
                c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val code = c.responseCode
            val stream = if (code >= 400) c.errorStream else c.inputStream
            val response = stream?.bufferedReader()?.use { it.readText() } ?: ""
            c.disconnect()
            HttpResult(code, response)
        } catch (e: Exception) {
            HttpResult(-1, "ERROR: " + e.message)
        }
    }

    data class HttpResult(val code: Int, val body: String)
}
