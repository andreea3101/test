import unittest
from unittest.mock import patch, MagicMock
import time
import serial # Moved import serial to the top for exceptions
from simulator.outputs.serial import SerialOutput, SerialOutputConfig

# No longer relying on SERIAL_PORT_LOOPBACK directly in tests using mocks.
# SERIAL_PORT_LOOPBACK = 'loop://'

class TestSerialOutput(unittest.TestCase):
    """Tests for the SerialOutput class."""

    @patch('simulator.outputs.serial.serial.Serial')
    def test_serial_output_lifecycle_and_send(self, mock_serial_class):
        """Test start, send, and stop functionality of SerialOutput with a mocked Serial port."""
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False # Initial state

        # Configure the mock_serial_class to return our mock_serial_instance
        mock_serial_class.return_value = mock_serial_instance

        config = SerialOutputConfig(
            port="/dev/ttyMock",  # Port name doesn't matter much with mock
            baudrate=9600,
            timeout=0.1,
            write_timeout=0.1
        )
        serial_output = SerialOutput(config)

        # Test start
        # When serial_output.start() is called, it should instantiate serial.Serial
        # and then that instance's is_open should become True (simulated by us)
        def fake_serial_open():
            mock_serial_instance.is_open = True
        mock_serial_instance.open = fake_serial_open # serial.Serial calls open() on itself if port is set at init
                                                  # or we can assume it's opened by constructor

        # To simulate serial.Serial constructor opening the port:
        # We need to ensure that when SerialOutput calls serial.Serial(...), the mock_serial_instance.is_open is set to True
        # A simple way: assume the mock is 'open' after instantiation if serial.Serial() doesn't raise error.
        # serial.Serial() itself calls self.open()
        # So, the mock_serial_class() call in SerialOutput.start() will result in mock_serial_instance.open() effectively.
        # We can make mock_serial_instance.is_open True after the constructor call.
        # A more direct way for the mock:
        mock_serial_class.side_effect = lambda *args, **kwargs: mock_serial_instance_factory(mock_serial_instance, *args, **kwargs)

        def mock_serial_instance_factory(instance, port, baudrate, bytesize, parity, stopbits, timeout, write_timeout):
            # Simulate the port opening successfully
            instance.port = port
            instance.is_open = True
            return instance

        serial_output.start()

        mock_serial_class.assert_called_once_with(
            port="/dev/ttyMock", baudrate=9600, bytesize=8,
            parity='N', stopbits=1, timeout=0.1, write_timeout=0.1
        )
        self.assertTrue(serial_output.is_running)
        self.assertIsNotNone(serial_output.serial_port)
        self.assertTrue(serial_output.serial_port.is_open) # Check our mock's state

        # NMEA sentence to send
        test_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"

        # Test send_sentence
        result = serial_output.send_sentence(test_sentence)
        self.assertTrue(result)
        self.assertEqual(serial_output.sentences_sent, 1)
        # Check that write was called on the mock serial instance
        expected_output = (test_sentence + '\r\n').encode('utf-8')
        mock_serial_instance.write.assert_called_once_with(expected_output)

        # Test sending multiple sentences
        mock_serial_instance.reset_mock() # Reset call counts for write
        for i in range(5):
            current_sentence = f"{test_sentence[:-3]}{i}*{47+i%10:02X}"
            result = serial_output.send_sentence(current_sentence)
            self.assertTrue(result)
            expected_output = (current_sentence + '\r\n').encode('utf-8')
            mock_serial_instance.write.assert_any_call(expected_output) # Use assert_any_call if order doesn't matter or assert_has_calls
        self.assertEqual(mock_serial_instance.write.call_count, 5)
        self.assertEqual(serial_output.sentences_sent, 6) # 1 + 5

        # Test stop
        serial_output.stop()
        self.assertFalse(serial_output.is_running)
        mock_serial_instance.close.assert_called_once()
        # is_open should be false after close, SerialOutput sets self.serial_port to None
        self.assertIsNone(serial_output.serial_port)


    @patch('simulator.outputs.serial.serial.Serial', side_effect=serial.SerialException("Test error"))
    def test_serial_output_start_failure(self, mock_serial_class_raising_exception):
        """Test failure to start serial output when serial.Serial raises an exception."""
        config = SerialOutputConfig(port="/dev/nonexistentport", baudrate=9600)
        serial_output = SerialOutput(config)

        with self.assertRaises(RuntimeError) as context:
            serial_output.start()

        mock_serial_class_raising_exception.assert_called_once()
        self.assertFalse(serial_output.is_running)
        self.assertIn("Failed to start serial output", str(context.exception))
        self.assertIn("Test error", str(context.exception)) # Check our specific error is there


    def test_serial_output_send_when_not_running(self):
        """Test sending a sentence when the serial output is not running."""
        # No need to mock serial.Serial here as it won't be called if not started
        config = SerialOutputConfig(port="/dev/ttyMock", baudrate=9600)
        serial_output = SerialOutput(config)
        # Do not start the output

        test_sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        result = serial_output.send_sentence(test_sentence)
        self.assertFalse(result)
        self.assertEqual(serial_output.sentences_sent, 0)

    @patch('simulator.outputs.serial.serial.Serial')
    def test_serial_output_get_status(self, mock_serial_class):
        """Test the get_status method."""
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False # Initial state
        mock_serial_class.return_value = mock_serial_instance

        def mock_serial_instance_factory(instance, port, baudrate, bytesize, parity, stopbits, timeout, write_timeout):
            instance.port = port # Keep track of port for status
            instance.is_open = True # Simulate open
            return instance
        mock_serial_class.side_effect = lambda *args, **kwargs: mock_serial_instance_factory(mock_serial_instance, *args, **kwargs)


        config = SerialOutputConfig(port="/dev/ttyMockStatus", baudrate=19200)
        serial_output = SerialOutput(config)

        status_before_start = serial_output.get_status()
        self.assertFalse(status_before_start['running'])
        self.assertEqual(status_before_start['port'], "/dev/ttyMockStatus")
        self.assertEqual(status_before_start['baudrate'], 19200)
        self.assertFalse(status_before_start['is_open']) # serial_port is None before start

        serial_output.start()
        status_after_start = serial_output.get_status()
        self.assertTrue(status_after_start['running'])
        self.assertTrue(status_after_start['is_open']) # Mocked to be open
        self.assertEqual(status_after_start['sentences_sent'], 0)

        serial_output.send_sentence("$TESTSEN,1*00")
        status_after_send = serial_output.get_status()
        self.assertEqual(status_after_send['sentences_sent'], 1)

        serial_output.stop()
        status_after_stop = serial_output.get_status()
        self.assertFalse(status_after_stop['running'])
        # After stop, serial_port is None, so get_status should reflect that for is_open
        self.assertFalse(status_after_stop['is_open'])


    @patch('simulator.outputs.serial.serial.Serial')
    def test_serial_output_context_manager(self, mock_serial_class):
        """Test SerialOutput as a context manager."""
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False

        def mock_serial_instance_factory(instance, port, baudrate, bytesize, parity, stopbits, timeout, write_timeout):
            instance.port = port
            instance.is_open = True # Simulate open
            return instance
        mock_serial_class.side_effect = lambda *args, **kwargs: mock_serial_instance_factory(mock_serial_instance, *args, **kwargs)

        config = SerialOutputConfig(port="/dev/ttyCtxMgr", baudrate=9600, timeout=0.1)

        with SerialOutput(config) as so:
            self.assertTrue(so.is_running)
            mock_serial_class.assert_called_once() # Check Serial was instantiated
            self.assertTrue(so.serial_port.is_open) # Check mock state
            so.send_sentence("$TESTCTX,1*00")
            self.assertEqual(so.sentences_sent, 1)
            so.serial_port.write.assert_called_with(b"$TESTCTX,1*00\r\n")

        # After exiting context, it should be stopped
        self.assertFalse(so.is_running)
        mock_serial_instance.close.assert_called_once()
        self.assertIsNone(so.serial_port) # SerialOutput sets it to None on stop

    @patch('simulator.outputs.serial.serial.Serial')
    def test_serial_output_correct_sentence_format(self, mock_serial_class):
        """Test that sentences are correctly formatted with CRLF."""
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False

        def mock_serial_instance_factory(instance, port, baudrate, bytesize, parity, stopbits, timeout, write_timeout):
            instance.port = port
            instance.is_open = True
            return instance
        mock_serial_class.side_effect = lambda *args, **kwargs: mock_serial_instance_factory(mock_serial_instance, *args, **kwargs)

        config = SerialOutputConfig(port="/dev/ttyFormat", baudrate=9600, timeout=0.1)
        serial_output = SerialOutput(config)
        serial_output.start()

        # Test sentence without CRLF
        sentence1 = "$GPGGA,data1"
        serial_output.send_sentence(sentence1)
        mock_serial_instance.write.assert_called_with((sentence1 + '\r\n').encode('utf-8'))

        # Test sentence already with CRLF
        sentence2 = "$GPRMC,data2\r\n"
        serial_output.send_sentence(sentence2)
        # Should be called with sentence2 as is, because it already has CRLF
        mock_serial_instance.write.assert_called_with(sentence2.encode('utf-8'))

        serial_output.stop()

    @patch('simulator.outputs.serial.serial.Serial')
    def test_serial_write_timeout(self, mock_serial_class):
        """Test serial write timeout exception handling."""
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.side_effect = serial.SerialTimeoutException("Write timeout")
        mock_serial_class.return_value = mock_serial_instance

        config = SerialOutputConfig(port="/dev/ttyTimeout", write_timeout=0.01)
        serial_output = SerialOutput(config)
        serial_output.start()

        result = serial_output.send_sentence("$TIMEOUTTEST*00")
        self.assertFalse(result)
        self.assertEqual(serial_output.sentences_sent, 0) # Should not increment on failure
        # Check console output or log for "Serial write timeout" - harder to test directly without capturing stdout

    @patch('simulator.outputs.serial.serial.Serial')
    def test_serial_write_generic_exception(self, mock_serial_class):
        """Test generic serial write exception handling."""
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.side_effect = serial.SerialException("Generic serial error")
        mock_serial_class.return_value = mock_serial_instance

        config = SerialOutputConfig(port="/dev/ttyGenEx")
        serial_output = SerialOutput(config)
        serial_output.start()

        result = serial_output.send_sentence("$GENEXCTEST*00")
        self.assertFalse(result)
        self.assertEqual(serial_output.sentences_sent, 0)


if __name__ == '__main__':
    # Need to import serial for SerialException and SerialTimeoutException if tests are run directly
    # This is usually handled by the test runner environment if pyserial is installed.
    import serial
    unittest.main()
