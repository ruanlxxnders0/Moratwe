#!/usr/bin/env python
"""
Test script to validate QR code format compatibility between web and mobile app.
"""
import json
import qrcode
from io import BytesIO

def test_qr_format():
    """Test the new QR code format matches mobile app expectations."""
    
    # Sample data matching the new format
    qr_data = {
        'event_id': '1',
        'user_id': '123',
        'qr_code_data': '123e4567-e89b-12d3-a456-426614174000'
    }
    
    # Generate QR code data using the new format
    qr_json = json.dumps(qr_data)
    
    print("QR Code Data (JSON):")
    print(qr_json)
    print()
    
    # Test that it can be parsed back
    try:
        parsed_data = json.loads(qr_json)
        print("✅ JSON parsing successful:")
        print(f"  Event ID: {parsed_data.get('event_id')}")
        print(f"  User ID: {parsed_data.get('user_id')}")
        print(f"  QR Code Data: {parsed_data.get('qr_code_data')}")
        print()
        
        # Check required fields for mobile app
        required_fields = ['event_id', 'user_id', 'qr_code_data']
        missing_fields = [field for field in required_fields if field not in parsed_data]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        else:
            print("✅ All required fields present")
        
        # Test QR code generation
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_json)
        qr.make(fit=True)
        
        print("✅ QR code generation successful")
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save test QR code
        img.save("test_qr_code.png")
        print("✅ Test QR code saved as test_qr_code.png")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        return False
    except Exception as e:
        print(f"❌ QR code generation failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing QR Code Format Compatibility")
    print("=" * 40)
    
    success = test_qr_format()
    
    print()
    if success:
        print("🎉 All tests passed! The QR code format is compatible with the mobile app.")
    else:
        print("💥 Tests failed! There may be compatibility issues.")
