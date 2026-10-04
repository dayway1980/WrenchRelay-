package com.wrenchrelay.industrial;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {
  private static final String HOME = "https://wrenchrelayllc.com/";
  private WebView web;

  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    web = new WebView(this);
    setContentView(web);
    WebSettings s = web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    s.setAllowFileAccess(false);
    s.setAllowContentAccess(false);
    web.setWebViewClient(new WebViewClient() {
      @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        Uri u = request.getUrl();
        String host = u.getHost() == null ? "" : u.getHost().toLowerCase();
        if (host.equals("wrenchrelayllc.com") || host.endsWith(".wrenchrelayllc.com")) return false;
        startActivity(new Intent(Intent.ACTION_VIEW, u));
        return true;
      }
    });
    web.loadUrl(HOME);
  }

  @Override public void onBackPressed() {
    if (web != null && web.canGoBack()) web.goBack(); else super.onBackPressed();
  }
}
