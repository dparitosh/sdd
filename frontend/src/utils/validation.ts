/**
 * Validation utilities
 * Common validation functions for forms and data
 */

/**
 * Validate email address
 * @param email - Email string to validate
 * @returns True if valid email
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate URL
 * @param url - URL string to validate
 * @returns True if valid URL
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate UUID
 * @param uuid - UUID string to validate
 * @returns True if valid UUID
 */
export function isValidUuid(uuid: string): boolean {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

/**
 * Validate required field
 * @param value - Value to check
 * @returns Error message or undefined if valid
 */
export function validateRequired(value: any): string | undefined {
  if (value == null || value === '' || (Array.isArray(value) && value.length === 0)) {
    return 'This field is required';
  }
  return undefined;
}

/**
 * Validate minimum length
 * @param value - String to check
 * @param min - Minimum length
 * @returns Error message or undefined if valid
 */
export function validateMinLength(value: string, min: number): string | undefined {
  if (value.length < min) {
    return `Must be at least ${min} characters`;
  }
  return undefined;
}

/**
 * Validate maximum length
 * @param value - String to check
 * @param max - Maximum length
 * @returns Error message or undefined if valid
 */
export function validateMaxLength(value: string, max: number): string | undefined {
  if (value.length > max) {
    return `Must be no more than ${max} characters`;
  }
  return undefined;
}

/**
 * Validate number range
 * @param value - Number to check
 * @param min - Minimum value
 * @param max - Maximum value
 * @returns Error message or undefined if valid
 */
export function validateRange(value: number, min: number, max: number): string | undefined {
  if (value < min || value > max) {
    return `Must be between ${min} and ${max}`;
  }
  return undefined;
}

/**
 * Sanitize HTML string
 * @param html - HTML string to sanitize
 * @returns Sanitized string
 */
export function sanitizeHtml(html: string): string {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
}

/**
 * Validate file type
 * @param file - File to validate
 * @param allowedTypes - Array of allowed MIME types or extensions
 * @returns Error message or undefined if valid
 */
export function validateFileType(file: File, allowedTypes: string[]): string | undefined {
  const fileExt = `.${file.name.split('.').pop()?.toLowerCase()}`;
  const isValid = allowedTypes.some(
    type => file.type === type || fileExt === type
  );
  
  if (!isValid) {
    return `File type not allowed. Allowed types: ${allowedTypes.join(', ')}`;
  }
  return undefined;
}

/**
 * Validate file size
 * @param file - File to validate
 * @param maxSizeBytes - Maximum size in bytes
 * @returns Error message or undefined if valid
 */
export function validateFileSize(file: File, maxSizeBytes: number): string | undefined {
  if (file.size > maxSizeBytes) {
    const maxMB = (maxSizeBytes / (1024 * 1024)).toFixed(2);
    return `File size must be less than ${maxMB} MB`;
  }
  return undefined;
}
