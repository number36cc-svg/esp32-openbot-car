/*
 * OpenBot 方向自动测试程序（ direction-test ）
 * 用途：装上电池后自动循环测试电机方向，无需手机/电脑/手柄
 * 流程：每一步 2 秒 + 停 1 秒，循环往复
 *
 *   [1] 左轮 正转    [2] 左轮 反转
 *   [3] 右轮 正转    [4] 右轮 反转
 *   [5] 全部 正转    [6] 全部 反转
 *
 * 观察方法：把车头朝向自己，"正转"时轮子应朝车头方向滚动（即向前）。
 * 记录哪个环节方向不对，报给聪聪的 AI 即可，两分钟改好重烧。
 *
 * 引脚（来自卖家源码）：
 *   左电机 IN1/IN2 = GPIO 19 / 21
 *   右电机 IN1/IN2 = GPIO 32 / 33
 *   两脚同高 = 刹车（MX1508）
 */

const int PIN_L1 = 19;
const int PIN_L2 = 21;
const int PIN_R1 = 32;
const int PIN_R2 = 33;

void brake() {
  digitalWrite(PIN_L1, HIGH);
  digitalWrite(PIN_L2, HIGH);
  digitalWrite(PIN_R1, HIGH);
  digitalWrite(PIN_R2, HIGH);
}

// coast：两脚同低 = 滑行（更接近真实行驶状态）
void coast() {
  digitalWrite(PIN_L1, LOW);
  digitalWrite(PIN_L2, LOW);
  digitalWrite(PIN_R1, LOW);
  digitalWrite(PIN_R2, LOW);
}

void run(bool left, bool forward, unsigned long ms) {
  int p1 = left ? PIN_L1 : PIN_R1;
  int p2 = left ? PIN_L2 : PIN_R2;
  digitalWrite(p1, forward ? HIGH : LOW);
  digitalWrite(p2, forward ? LOW : HIGH);
  delay(ms);
  brake();
  delay(300);
  coast();
  delay(700);
}

void setup() {
  pinMode(PIN_L1, OUTPUT);
  pinMode(PIN_L2, OUTPUT);
  pinMode(PIN_R1, OUTPUT);
  pinMode(PIN_R2, OUTPUT);
  coast();
  Serial.begin(115200);
  Serial.println();
  Serial.println("=== OpenBot 电机方向自动测试 ===");
}

void loop() {
  Serial.println("[1] 左轮 正转(期望:向前滚)");
  run(true, true, 2000);

  Serial.println("[2] 左轮 反转(期望:向后滚)");
  run(true, false, 2000);

  Serial.println("[3] 右轮 正转(期望:向前滚)");
  run(false, true, 2000);

  Serial.println("[4] 右轮 反转(期望:向后滚)");
  run(false, false, 2000);

  Serial.println("[5] 全部 正转(期望:车向前)");
  run(true, true, 2000);
  run(false, true, 2000);

  Serial.println("[6] 全部 反转(期望:车向后)");
  run(true, false, 2000);
  run(false, false, 2000);

  Serial.println("--- 一轮结束，3 秒后重复 ---");
  delay(3000);
}
