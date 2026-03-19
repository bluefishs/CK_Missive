/**
 * ProfilePage shared types
 *
 * @version 1.0.0
 */

import type { User } from '../../types/api';

/** Fields submitted when saving profile updates */
export interface ProfileUpdatePayload {
  username: string;
  full_name: string;
  department?: string;
  position?: string;
}

/** All fields displayed in the profile form (includes read-only email) */
export interface ProfileFormFields extends ProfileUpdatePayload {
  email?: string;
}

export interface PasswordChangeFormValues {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ProfileInfoCardProps {
  profile: User;
  isMobile: boolean;
  editing: boolean;
  saving: boolean;
  onToggleEdit: () => void;
  onSave: (values: ProfileUpdatePayload) => Promise<void>;
  onCancelEdit: () => void;
}

export interface AccountInfoCardProps {
  profile: User;
  isMobile: boolean;
}

export interface PasswordChangeModalProps {
  open: boolean;
  isMobile: boolean;
  onCancel: () => void;
  onSubmit: (values: PasswordChangeFormValues) => Promise<void>;
}
