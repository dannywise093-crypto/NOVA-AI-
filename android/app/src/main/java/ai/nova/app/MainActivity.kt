package ai.nova.app

import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import java.net.HttpURLConnection
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {
    private val prefs by lazy { getSharedPreferences("nova", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 24)
        }
        val title = TextView(this).apply { text = "NOVA AI"; textSize = 28f }
        val status = TextView(this).apply { text = "Backend: not tested"; textSize = 14f }
        val endpoint = EditText(this).apply {
            hint = "API base URL"
            setText(prefs.getString("api", "http://10.0.2.2:8000"))
        }
        val test = Button(this).apply { text = "Test Backend" }
        val input = EditText(this).apply { hint = "Message NOVA"; minLines = 2 }
        val send = Button(this).apply { text = "Send" }
        val output = TextView(this).apply { text = "Ready."; textSize = 16f }
        root.addView(title); root.addView(status); root.addView(endpoint); root.addView(test)
        root.addView(input); root.addView(send); root.addView(output)
        setContentView(root)

        test.setOnClickListener {
            val base = endpoint.text.toString().trim().trimEnd('/')
            prefs.edit().putString("api", base).apply()
            status.text = "Testing..."
            thread {
                val result = get("$base/")
                runOnUiThread {
                    status.text = if (result.startsWith("ERROR")) result else "Backend: online"
                    output.text = result
                }
            }
        }
        send.setOnClickListener {
            output.text = "Backend connectivity works; authenticated chat integration is next."
        }
    }

    private fun get(url: String): String = try {
        val c = URL(url).openConnection() as HttpURLConnection
        c.connectTimeout = 5000
        c.readTimeout = 5000
        c.requestMethod = "GET"
        val body = c.inputStream.bufferedReader().readText()
        c.disconnect()
        body
    } catch (err: Exception) {
        "ERROR: " + err.message
    }
}
