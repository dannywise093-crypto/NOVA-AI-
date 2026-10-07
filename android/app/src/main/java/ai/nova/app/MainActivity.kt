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
    private val history = mutableListOf<JSONObject>()

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
        val header = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
        }
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

    private fun bubble(text: String, user: Boolean) {
        val view = TextView(this).apply {
            this.text = text
            textSize = 16f
            setTextColor(Color.WHITE)
            setPadding(18, 14, 18, 14)
            setBackgroundColor(if (user) Color.rgb(45, 45, 55) else Color.rgb(28, 42, 36))
        }
        val params = LinearLayout.LayoutParams(-1, -2).apply {
            setMargins(0, 8, 0, 8)
        }
        messages.addView(view, params)
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
        } catch (e: Exception) {
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
        if (messages.childCount == 0) bubble("I'm NOVA. Ask me anything.", false)
    }

    private fun sendMessage() {
        val text = message.text.toString().trim()
        val token = prefs.getString("token", null) ?: return
        if (text.isBlank()) return
        val historyArray = JSONArray()
        history.forEach { historyArray.put(it) }

        bubble(text, true)
        message.text.clear()
        sendButton.isEnabled = false
        status.text = "Thinking..."
        val placeholder = TextView(this).apply {
            text = "NOVA is thinking..."
            setTextColor(Color.LTGRAY)
            textSize = 15f
            setPadding(18, 14, 18, 14)
        }
        messages.addView(placeholder)

        thread {
            val result = request("POST", prefs.getString("api", "")!!.trimEnd('/') + "/api/chat",
                JSONObject().put("message", text).put("history", historyArray),
                "Bearer $token")
            if (result.code in 200..299) {
                try {
                    val json = JSONObject(result.body)
                    val answer = json.optString("content", "No response.")
                    history.add(JSONObject().put("role", "user").put("content", text))
                    history.add(JSONObject().put("role", "assistant").put("content", answer))
                    runOnUiThread {
                        messages.removeView(placeholder)
                        bubble(answer, false)
                        sendButton.isEnabled = true
                        status.text = "● Ready"
                    }
                } catch (e: Exception) {
                    runOnUiThread { messages.removeView(placeholder); authError("Invalid response") }
                }
            } else if (result.code == 401) {
                prefs.edit().remove("token").apply()
                runOnUiThread { messages.removeView(placeholder); status.text = "Session expired"; sendButton.isEnabled = false }
            } else {
                runOnUiThread { messages.removeView(placeholder); authError("Chat failed: " + result.body) }
            }
        }
    }

    private fun authError(text: String) {
        status.text = text
        authButton.isEnabled = true
    }

    private fun request(method: String, url: String, body: JSONObject? = null, auth: String? = null): HttpResult {
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
