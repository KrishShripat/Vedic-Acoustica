import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { authFetch } from '../utils/auth'

const getFullName = (user) =>
  [user.first_name, user.last_name].filter(Boolean).join(' ').trim() || user.username || ''

const getInitials = (name) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join('').toUpperCase()

const getErrorMessage = (data, statusCode, action) => {
  if (data.error || data.detail) return data.error || data.detail
  const fieldErrors = Object.values(data).flat().filter(value => typeof value === 'string')
  return fieldErrors.join(' ') || `${action} failed (HTTP ${statusCode}).`
}

export default function ProfileModal({
  user,
  apiBase,
  onClose,
  onUserUpdated,
  onAccountDeleted,
}) {
  const [editing, setEditing] = useState(false)
  const [username, setUsername] = useState(user.username || '')
  const [name, setName] = useState(getFullName(user))
  const [saving, setSaving] = useState(false)
  const [deletionStep, setDeletionStep] = useState(null)
  const [deleteConfirmation, setDeleteConfirmation] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const usernameInput = useRef(null)
  const deleteConfirmationInput = useRef(null)

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key !== 'Escape' || saving || deleting) return
      if (deletionStep) {
        setDeletionStep(null)
        setDeleteConfirmation('')
        setDeleteError('')
      } else {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [deletionStep, deleting, onClose, saving])

  useEffect(() => {
    if (editing) usernameInput.current?.focus()
  }, [editing])

  useEffect(() => {
    if (deletionStep === 'confirm') deleteConfirmationInput.current?.focus()
  }, [deletionStep])

  const beginEditing = () => {
    setUsername(user.username || '')
    setName(getFullName(user))
    setError('')
    setSuccess('')
    setEditing(true)
  }

  const cancelEditing = () => {
    setUsername(user.username || '')
    setName(getFullName(user))
    setError('')
    setEditing(false)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const trimmedUsername = username.trim()
    const trimmedName = name.trim()
    if (!trimmedUsername || !trimmedName) {
      setError('Name and username cannot be empty.')
      return
    }

    const [firstName, ...lastNameParts] = trimmedName.split(/\s+/)
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const response = await authFetch(`${apiBase}/auth/me/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: trimmedUsername,
          first_name: firstName,
          last_name: lastNameParts.join(' '),
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(getErrorMessage(data, response.status, 'Profile update'))
      }

      onUserUpdated(data.user)
      setUsername(data.user.username || '')
      setName(getFullName(data.user))
      setEditing(false)
      setSuccess('Profile updated successfully.')
    } catch (saveError) {
      setError(saveError.message || 'Could not save your profile. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const beginAccountDeletion = () => {
    setEditing(false)
    setDeletionStep('warning')
    setDeleteConfirmation('')
    setDeleteError('')
  }

  const cancelAccountDeletion = () => {
    if (deleting) return
    setDeletionStep(null)
    setDeleteConfirmation('')
    setDeleteError('')
  }

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== 'DELETE' || deleting) return
    setDeleting(true)
    setDeleteError('')
    try {
      const response = await authFetch(`${apiBase}/auth/delete-account/`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation: deleteConfirmation }),
      })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(getErrorMessage(data, response.status, 'Account deletion'))
      }
      onAccountDeleted()
    } catch (deleteError) {
      setDeleteError(deleteError.message || 'Account deletion failed. Please try again.')
    } finally {
      setDeleting(false)
    }
  }

  const role = user.is_superuser ? 'Administrator' : user.is_staff ? 'Staff' : 'User'
  const displayName = getFullName(user)

  return createPortal(
    <div
      className="profile-backdrop"
      onMouseDown={(event) => {
        if (event.target !== event.currentTarget || saving || deleting) return
        if (deletionStep) {
          cancelAccountDeletion()
        } else {
          onClose()
        }
      }}
    >
      <section
        className={`profile-dialog ${deletionStep ? 'account-delete-dialog' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={deletionStep ? 'account-delete-title' : 'profile-title'}
      >
        {deletionStep ? (
          <>
            <div className="profile-dialog-heading">
              <div>
                <span className="eyebrow account-delete-eyebrow">
                  {deletionStep === 'warning' ? 'Permanent account action' : 'Final confirmation'}
                </span>
                <h2 id="account-delete-title">
                  {deletionStep === 'warning' ? 'Delete your account?' : 'Confirm permanent deletion'}
                </h2>
              </div>
              <button
                className="profile-close"
                type="button"
                onClick={cancelAccountDeletion}
                disabled={deleting}
                aria-label="Cancel account deletion"
              >
                ×
              </button>
            </div>

            {deletionStep === 'warning' ? (
              <>
                <div className="account-delete-warning" role="alert">
                  <strong>Are you sure you want to permanently delete your account?</strong>
                  <p>
                    This action cannot be undone. Your profile and recordings uploaded
                    under this account, including their analysis results, will be
                    permanently deleted. You will not be able to recover this data.
                    Existing shared recordings that are not owned by your account
                    will not be affected.
                  </p>
                </div>
                <div className="profile-actions">
                  <button
                    className="engraved-button small profile-secondary-action"
                    type="button"
                    onClick={cancelAccountDeletion}
                  >
                    Cancel
                  </button>
                  <button
                    className="engraved-button small account-delete-button"
                    type="button"
                    onClick={() => setDeletionStep('confirm')}
                  >
                    Delete Permanently
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="account-delete-instruction">
                  To confirm, type <strong>DELETE</strong> exactly as shown. Your account
                  and its owned recordings will then be permanently removed.
                </p>
                <label className="account-delete-field">
                  <span>Type DELETE to continue</span>
                  <input
                    ref={deleteConfirmationInput}
                    value={deleteConfirmation}
                    onChange={(event) => setDeleteConfirmation(event.target.value)}
                    autoComplete="off"
                    autoCapitalize="none"
                    spellCheck="false"
                    disabled={deleting}
                  />
                </label>
                {deleteError && (
                  <p className="profile-message error-inscription" role="alert">{deleteError}</p>
                )}
                <div className="profile-actions">
                  <button
                    className="engraved-button small profile-secondary-action"
                    type="button"
                    onClick={cancelAccountDeletion}
                    disabled={deleting}
                  >
                    Cancel
                  </button>
                  <button
                    className="engraved-button small account-delete-button"
                    type="button"
                    onClick={handleDeleteAccount}
                    disabled={deleteConfirmation !== 'DELETE' || deleting}
                  >
                    {deleting ? 'Deleting…' : 'Permanently Delete Account'}
                  </button>
                </div>
              </>
            )}
          </>
        ) : (
          <>
            <div className="profile-dialog-heading">
              <div>
                <span className="eyebrow">Account details</span>
                <h2 id="profile-title">Profile</h2>
              </div>
              <button
                className="profile-close"
                type="button"
                onClick={onClose}
                disabled={saving}
                aria-label="Close profile"
              >
                ×
              </button>
            </div>

            <div className="profile-person">
              <span className="profile-avatar" aria-hidden="true">{getInitials(displayName)}</span>
              <div>
                <strong>{displayName}</strong>
                <span>@{user.username || '—'}</span>
              </div>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="profile-fields">
                <label className="profile-field">
                  <span>Name</span>
                  {editing
                    ? <input value={name} onChange={event => setName(event.target.value)} maxLength={301} autoComplete="name" />
                    : <strong>{displayName}</strong>}
                </label>
                <label className="profile-field">
                  <span>Username</span>
                  {editing
                    ? <input
                      ref={usernameInput}
                      value={username}
                      onChange={event => setUsername(event.target.value)}
                      maxLength={150}
                      autoComplete="username"
                    />
                    : <strong>{user.username || '—'}</strong>}
                </label>
                <div className="profile-field">
                  <span>Email</span>
                  <strong>{user.email || '—'}</strong>
                  <small>Read only</small>
                </div>
                <div className="profile-field">
                  <span>Role</span>
                  <strong>{role}</strong>
                </div>
                <div className="profile-field">
                  <span>Account status</span>
                  <strong>{user.is_active ? 'Active' : 'Inactive'}</strong>
                </div>
              </div>

              {error && <p className="profile-message error-inscription" role="alert">{error}</p>}
              {success && <p className="profile-message profile-success" role="status">{success}</p>}

              <div className="profile-actions">
                {editing ? (
                  <>
                    <button className="engraved-button small" type="button" onClick={cancelEditing} disabled={saving}>
                      Cancel
                    </button>
                    <button className="engraved-button small" type="submit" disabled={saving}>
                      {saving ? 'Saving…' : 'Save changes'}
                    </button>
                  </>
                ) : (
                  <>
                    <button className="engraved-button small" type="button" onClick={beginEditing}>
                      Edit profile
                    </button>
                    <button className="engraved-button small profile-secondary-action" type="button" onClick={onClose}>
                      Close
                    </button>
                  </>
                )}
              </div>
            </form>

            {!editing && (
              <div className="profile-danger-zone">
                <p>Permanently remove this account and its owned recordings.</p>
                <button
                  className="profile-delete-trigger"
                  type="button"
                  onClick={beginAccountDeletion}
                >
                  Delete Account
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>,
    document.body,
  )
}
