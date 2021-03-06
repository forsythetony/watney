import asyncio
import time
import RPi.GPIO as GPIO
from events import Events


class ServoController:

    def __init__(self, config):
        Events.getInstance().janusFirstConnect.append(lambda: self.onJanusConnected())

        servoConfig = config["SERVO"]
        self.pwmPin = int(servoConfig["PWMPin"])
        self.neutral = float(servoConfig["Neutral"])
        self.min = float(servoConfig["Min"])
        self.max = float(servoConfig["Max"])

        self.frequency = 50

        self.changeVelocityPerSec = 2
        # 1 is forward, -1 is backward, 0 is stop
        self.direction = 0
        self.timingLock = asyncio.Condition()
        self.task = None
        self.pwmControl = None
        self.startServo()


    async def forward(self):
        async with self.timingLock:
            self.direction = 1
            self.timingLock.notify()

    async def backward(self):
        async with self.timingLock:
            self.direction = -1
            self.timingLock.notify()

    async def lookStop(self):
        async with self.timingLock:
            if self.direction != 0:
                self.direction = 0
                self.timingLock.notify()

    def onJanusConnected(self):
        loop = asyncio.get_event_loop()
        self.task = loop.create_task(self.timingLoop())

    async def timingLoop(self):
        print("Servo starting...")

        try:
            initialSleep = 0.25
            # go neutral first
            self.pwmControl.ChangeDutyCycle(self.neutral)
            await asyncio.sleep(initialSleep)
            self.pwmControl.ChangeDutyCycle(self.max)
            await asyncio.sleep(initialSleep)
            self.pwmControl.ChangeDutyCycle(self.min)
            await asyncio.sleep(initialSleep)
            self.pwmControl.ChangeDutyCycle(self.neutral)
            await asyncio.sleep(initialSleep)
            self.pwmControl.ChangeDutyCycle(0)

            currentPosition = self.neutral
            lastChangeTime = None
            while True:
                async with self.timingLock:
                    if not self.__shouldBeMoving(currentPosition):
                        self.stopServo()
                        lastChangeTime = None
                        await self.timingLock.wait()
                        self.startServo()

                if not lastChangeTime:
                    changeDelta = 0
                else:
                    timeDelta = time.time() - lastChangeTime
                    changeDelta = self.changeVelocityPerSec * timeDelta

                lastChangeTime = time.time()

                if self.direction == 1:
                    currentPosition = min(currentPosition + changeDelta, self.max)
                elif self.direction == -1:
                    currentPosition = max(currentPosition - changeDelta, self.min)

                self.changeServo(currentPosition)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            self.stopServo()
            print("Servo stopped")
        except Exception as e:
            print("Unexpected exception in servo: " + str(e))

    def __shouldBeMoving(self, currentPosition):
        if self.direction == 0:
            return False
        elif self.direction == 1 and currentPosition >= self.max:
            return False
        elif self.direction == -1 and currentPosition <= self.min:
            return False

        return True

    def startServo(self):
        GPIO.setup(self.pwmPin, GPIO.OUT)
        self.pwmControl = GPIO.PWM(self.pwmPin, self.frequency)
        self.pwmControl.start(0)

    def stopServo(self):
        if self.pwmControl is not None:
            self.pwmControl.stop()
            self.pwmControl = None
        GPIO.setup(self.pwmPin, GPIO.IN)

    def changeServo(self, val):
        self.pwmControl.ChangeDutyCycle(val)
