package com.wrenchrelay.industrial;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import org.junit.Test;

public class WebHostPolicyTest {
  @Test public void acceptsOnlyTrustedSecureOrigins() {
    assertTrue(WebHostPolicy.isTrustedHttps("https://wrenchrelayllc.com/"));
    assertTrue(WebHostPolicy.isTrustedHttps("https://wrenchrelayllc.com/privacy"));
    assertTrue(WebHostPolicy.isTrustedHttps("https://wrenchrelayllc.com/delete-account"));
    assertTrue(WebHostPolicy.isTrustedHttps("https://www.wrenchrelayllc.com/industrial"));
    assertTrue(WebHostPolicy.isTrustedHttps("https://app.wrenchrelayllc.com/"));
    assertFalse(WebHostPolicy.isTrustedHttps("http://wrenchrelayllc.com"));
    assertFalse(WebHostPolicy.isTrustedHttps("https://wrenchrelayllc.com.attacker.example/"));
    assertFalse(WebHostPolicy.isTrustedHttps("https://evilwrenchrelayllc.com/"));
    assertFalse(WebHostPolicy.isTrustedHttps("https://user@wrenchrelayllc.com"));
    assertFalse(WebHostPolicy.isTrustedHttps("https://wrenchrelay.com"));
    assertFalse(WebHostPolicy.isTrustedHttps("javascript:alert(1)"));
    assertFalse(WebHostPolicy.isTrustedHttps("file:///tmp/test.html"));
    assertFalse(WebHostPolicy.isTrustedHttps(null));
  }

  @Test public void externalIntentsAreRestrictedToSafeSchemes() {
    assertTrue(WebHostPolicy.canOpenExternally("https://accounts.google.com/"));
    assertTrue(WebHostPolicy.canOpenExternally("mailto:support@example.com"));
    assertTrue(WebHostPolicy.canOpenExternally("tel:+15551234567"));
    assertFalse(WebHostPolicy.canOpenExternally("intent://scan/#Intent;end"));
    assertFalse(WebHostPolicy.canOpenExternally("file:///etc/passwd"));
    assertFalse(WebHostPolicy.canOpenExternally("javascript:alert(1)"));
    assertFalse(WebHostPolicy.canOpenExternally("https://user@example.com/"));
  }
}
