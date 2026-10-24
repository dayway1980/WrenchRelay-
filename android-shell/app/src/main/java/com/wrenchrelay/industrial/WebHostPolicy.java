package com.wrenchrelay.industrial;

import java.net.URI;
import java.util.Locale;

/** Strict first-party navigation guard. Does not trust lookalike domains. */
public final class WebHostPolicy {
  private WebHostPolicy() {}

  public static boolean isTrustedHttps(String value) {
    try {
      if (value == null) return false;
      URI uri = new URI(value);
      if (!"https".equalsIgnoreCase(uri.getScheme())) return false;
      String host = uri.getHost();
      if (host == null || uri.getUserInfo() != null) return false;
      host = host.toLowerCase(Locale.ROOT);
      return host.equals("wrenchrelayllc.com") || host.endsWith(".wrenchrelayllc.com");
    } catch (Exception e) {
      return false;
    }
  }

  public static boolean canOpenExternally(String value) {
    try {
      if (value == null) return false;
      URI uri = new URI(value);
      String scheme = uri.getScheme();
      if (scheme == null) return false;
      switch (scheme.toLowerCase(Locale.ROOT)) {
        case "http":
        case "https":
          return uri.getHost() != null && uri.getUserInfo() == null;
        case "mailto":
        case "tel":
          return true;
        default:
          return false;
      }
    } catch (Exception e) {
      return false;
    }
  }
}
